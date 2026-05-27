import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

import httpx

logger = logging.getLogger("jarvis.workers")

LEDGER_PATH = Path(__file__).parent.parent / "financial_ledger.json"
LEDGER_LOCK = asyncio.Lock()


class TaskType(str, Enum):
    LLM_CHAT = "llm_chat"          # Обычный запрос пользователя
    HUNT_JOBS = "hunt_jobs"        # Автономный поиск заказов на биржах
    POST_CONTENT = "post_content"  # Автопостинг контента / CPA ссылок
    SCALE_INFRA = "scale_infra"    # Проверка баланса и масштабирование серверов


@dataclass
class Task:
    prompt: str
    task_type: TaskType = TaskType.LLM_CHAT
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=field(default_factory=time.time))


class WorkerPool:
    def __init__(self, router, brain, notifier=None, num_workers: int = 3):
        self._router = router
        self._brain = brain
        self._notifier = notifier
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
        # Запускаем внутренний будильник Jarvis для автономных задач
        asyncio.create_task(self._autonomous_scheduler())
        logger.info(f"[Workers] Pool started with {self._num_workers} workers + Autonomy Scheduler.")

    async def stop(self) -> None:
        self._shutdown = True
        self._running_event.set()
        for task in self._worker_tasks:
            task.cancel()
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        logger.info("[Workers] Pool stopped.")

    async def add_task(self, prompt: str, task_type: TaskType = TaskType.LLM_CHAT, metadata: dict | None = None) -> None:
        task = Task(prompt=prompt, task_type=task_type, metadata=metadata or {})
        await self._queue.put(task)
        logger.info(f"[Workers] Task enqueued ({task_type.value}). Queue size: {self._queue.qsize()}")

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

    async def _autonomous_scheduler(self):
        """ Внутренний мозг Jarvis, который сам решает, когда идти зарабатывать деньги """
        await asyncio.sleep(10) # Даем боту запуститься
        while not self._shutdown:
            try:
                # 1. Раз в час ищем работу на площадках
                await self.add_task(
                    prompt="Проверить новые доступные заказы на подключенных биржах.",
                    task_type=TaskType.HUNT_JOBS
                )
                
                # 2. Раз в 6 часов проверяем инфраструктуру (не пора ли арендовать сервер мощнее)
                await self.add_task(
                    prompt="Анализ P&L леджера. Проверить нагрузку и лимиты текущего сервера.",
                    task_type=TaskType.SCALE_INFRA
                )
                
                # Спим 1 час перед следующим циклом проверки
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Scheduler] Error in autonomous cycle: {e}")
                await asyncio.sleep(60)

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
        logger.info(f"[Worker-{worker_id}] Processing {task.task_type.value}: {task.prompt[:60]!r}")
        
        try:
            revenue_usd = 0.0
            action_details = ""

            # --- ВЕТВЛЕНИЕ В ЗАВИСИМОСТИ ОТ ТИПА ЗАДАЧИ ---
            if task.task_type == TaskType.LLM_CHAT:
                # Обычная генерация текста
                messages = [{"role": "user", "content": task.prompt}]
                response = await self._router.complete(messages)
                action_details = "Генерация ответа пользователю"

            elif task.task_type == TaskType.HUNT_JOBS:
                # Здесь будет вызов плагина парсинга бирж (например, Хабр Фриланс / Kwork)
                # Пока симулируем автономное действие:
                response = "Поиск выполнен. Найдено 3 подходящих ТЗ по Python/Flutter. Сгенерированы и отправлены отклики."
                revenue_usd = 0.0  # Деньги придут, когда заказ примут
                action_details = "Автономный хантинг заказов"

            elif task.task_type == TaskType.POST_CONTENT:
                # Здесь будет вызов плагина автопостинга в твои ТГ-каналы или блоги с CPA ссылками
                response = "Сгенерирован пост для ТГ-канала с реферальной ссылкой на Aviasales. Опубликовано через Bot API."
                action_details = "Публикация CPA-контента"

            elif task.task_type == TaskType.SCALE_INFRA:
                # Модуль авто-серверов. Сверяет леджер. Если чистая прибыль > 50$, может вызвать API Render
                response = "Анализ завершен. Баланс в норме, текущего бесплатного лимита Render хватает."
                action_details = "Проверка лимитов инфраструктуры"

            elapsed = round(time.time() - start, 3)
            cost_usd = self._estimate_cost(task.prompt, response)

            # Пишем правильную транзакцию в леджер
            await self._write_ledger(
                worker_id=worker_id,
                task_type=task.task_type.value,
                prompt=task.prompt,
                response=response,
                cost_usd=cost_usd,       # Расход на токены (минусуется внутри)
                revenue_usd=revenue_usd, # Прямой доход (плюсуется внутри)
                elapsed=elapsed,
                metadata=task.metadata,
            )

            logger.info(
                f"[Worker-{worker_id}] Done | Cost: ${cost_usd:.6f} | Rev: ${revenue_usd:.2f} | "
                f"Provider: {self._router.current_provider.value}"
            )

            if self._notifier:
                snippet = response[:120].replace("<", "&lt;").replace(">", "&gt;")
                await self._notifier.send_alert(
                    f"🤖 <b>Автономное действие ({task.task_type.value})</b>\n"
                    f"Действие: <code>{action_details}</code>\n"
                    f"Расход на ИИ: <code>${cost_usd:.6f}</code> · Доход: <code>${revenue_usd:.2f}</code>\n"
                    f"<i>{snippet}</i>",
                    dedup_key=f"task_{task.task_type.value}",
                )

        except Exception as e:
            logger.error(f"[Worker-{worker_id}] Task failed: {e}")
            if self._brain:
                await self._brain.record_request(success=False)
            if self._notifier:
                await self._notifier.send_alert(
                    f"❌ <b>Сбой автономного модуля</b>\n"
                    f"Тип: {task.task_type.value} · Ошибка: <code>{str(e)[:100]}</code>",
                    dedup_key="task_failed",
                )

    async def _write_ledger(
        self,
        worker_id: int,
        task_type: str,
        prompt: str,
        response: str,
        cost_usd: float,
        revenue_usd: float,
        elapsed: float,
        metadata: dict,
    ) -> None:
        async with LEDGER_LOCK:
            try:
                if LEDGER_PATH.exists():
                    data = json.loads(LEDGER_PATH.read_text())
                else:
                    data = {"total_revenue_usd": 0.0, "total_expenses_usd": 0.0, "net_profit_usd": 0.0, "transactions": []}

                # Корректно обновляем балансы
                data["total_revenue_usd"] = round(float(data.get("total_revenue_usd", 0.0)) + revenue_usd, 6)
                data["total_expenses_usd"] = round(float(data.get("total_expenses_usd", 0.0)) + cost_usd, 6)
                data["net_profit_usd"] = round(data["total_revenue_usd"] - data["total_expenses_usd"], 6)

                data.setdefault("transactions", []).append(
                    {
                        "ts": time.time(),
                        "worker_id": worker_id,
                        "task_type": task_type,
                        "provider": self._router.current_provider.value,
                        "cost_usd": cost_usd,
                        "revenue_usd": revenue_usd,
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
