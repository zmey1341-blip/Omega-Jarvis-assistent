import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("jarvis.main")


async def main():
    from core.brain import brain
    from core.fail_safe_routing import FailSafeRouter
    from modules.admin_dashboard import start_bot
    from modules.tma_server import start_server

    router = FailSafeRouter(brain=brain)
    logger.info("[Main] FailSafeRouter initialized. Cascade: Gemini → OpenAI → Zhipu → OpenRouter → Ollama")

    bot_task = asyncio.create_task(start_bot(brain), name="telegram-bot")
    server_task = asyncio.create_task(start_server(brain), name="tma-server")

    logger.info("[Main] All services started. Running...")

    try:
        await asyncio.gather(bot_task, server_task)
    except asyncio.CancelledError:
        logger.info("[Main] Shutdown requested.")
    except Exception as e:
        logger.exception(f"[Main] Fatal error: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[Main] Interrupted by user. Exiting.")
