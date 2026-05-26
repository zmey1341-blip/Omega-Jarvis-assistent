import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("jarvis.workers")

LEDGER_PATH = Path(__file__).parent.parent / "financial_ledger.json"
LEDGER_LOCK = asyncio.Lock()


@dataclass
class Task:
    prompt: str
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class WorkerPool:
    def __init__(self, router, brain, num_workers: int = 3):
        self._router = router
        self._brain = brain
        self._num_workers = num_workers
        self._queue: asyncio.Queue[Task] = asyncio.Queue()
        self._running_event = asyncio.Event()
        self._running_event.set()
        self._worker_tasks: list[asyncio.Task] = []
        self._shutdown = False

    async def start(self) -> None:
        self._shutdown = False
        self._worker_tasks = [
            asyncio.create_task(self._worker_loop(i), name=f"worker-{i}")
            for i in range(self._num_workers)
        ]
        logger.info(f"[Workers] Pool started with {self._num_workers} workers.")

    async def stop(self) -> None:
        self._shutdown = True
        self._running_event.set()
        for task in self._worker_tasks:
            task.cancel()
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        logger.info("[Workers] Pool stopped.")

    async def add_task(self, prompt: str, metadata: dict | None = None) -> None:
        task = Task(prompt=prompt, metadata=metadata or {})
        await self._queue.put(task)
        logger.info(f"[Workers] Task enqueued. Queue size: {self._queue.qsize()}")

    async def pause(self) -> None:
        self._running_event.clear()
        await self._brain.pause_workers()
        logger.info("[Workers] All workers paused.")

    async def resume(self) -> None:
        self._running_event.set()
        await self._brain.resume_workers()
        logger.info("[Workers] All workers resumed.")

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    async def _worker_loop(self, worker_id: int) -> None:
        logger.info(f"[Worker-{worker_id}] Started.")
        while not self._shutdown:
            try:
                await self._running_event.wait()

                try:
                    task: Task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                await self._process_task(worker_id, task)
                self._queue.task_done()

            except asyncio.CancelledError:
                logger.info(f"[Worker-{worker_id}] Cancelled.")
                break
            except Exception as e:
                logger.exception(f"[Worker-{worker_id}] Unexpected error in loop: {e}")
                await asyncio.sleep(1.0)

        logger.info(f"[Worker-{worker_id}] Stopped.")

    async def _process_task(self, worker_id: int, task: Task) -> None:
        start = time.time()
        logger.info(f"[Worker-{worker_id}] Processing task: {task.prompt[:60]!r}")
        try:
            messages = [{"role": "user", "content": task.prompt}]
            response = await self._router.complete(messages)
            elapsed = round(time.time() - start, 3)

            cost_usd = self._estimate_cost(task.prompt, response)
            await self._write_ledger(
                worker_id=worker_id,
                prompt=task.prompt,
                response=response,
                cost_usd=cost_usd,
                elapsed=elapsed,
                metadata=task.metadata,
            )
            logger.info(
                f"[Worker-{worker_id}] Done in {elapsed}s | "
                f"cost=${cost_usd:.4f} | "
                f"provider={self._router.current_provider.value}"
            )
        except Exception as e:
            logger.error(f"[Worker-{worker_id}] Task failed, skipping: {e}")
            await self._brain.record_request(success=False)

    async def _write_ledger(
        self,
        worker_id: int,
        prompt: str,
        response: str,
        cost_usd: float,
        elapsed: float,
        metadata: dict,
    ) -> None:
        async with LEDGER_LOCK:
            try:
                if LEDGER_PATH.exists():
                    data = json.loads(LEDGER_PATH.read_text())
                else:
                    data = {"total_profit_usd": 0.0, "transactions": []}

                data["total_profit_usd"] = round(
                    float(data.get("total_profit_usd", 0.0)) + cost_usd, 6
                )
                data.setdefault("transactions", []).append(
                    {
                        "ts": time.time(),
                        "worker_id": worker_id,
                        "provider": self._router.current_provider.value,
                        "cost_usd": cost_usd,
                        "elapsed_sec": elapsed,
                        "prompt_snippet": prompt[:80],
                        "response_snippet": response[:80],
                        "metadata": metadata,
                    }
                )
                data["transactions"] = data["transactions"][-500:]

                LEDGER_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            except Exception as e:
                logger.error(f"[Workers] Failed to write ledger: {e}")

    @staticmethod
    def _estimate_cost(prompt: str, response: str) -> float:
        tokens_in = len(prompt.split()) * 1.3
        tokens_out = len(response.split()) * 1.3
        return round((tokens_in / 1_000_000) * 0.15 + (tokens_out / 1_000_000) * 0.60, 8)
