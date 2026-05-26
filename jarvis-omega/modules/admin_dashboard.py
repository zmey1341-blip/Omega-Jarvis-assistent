import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

logger = logging.getLogger("jarvis.admin")


def create_admin_router(brain):
    from aiogram import Router

    router = Router()
    admin_id = int(os.getenv("TELEGRAM_ADMIN_ID", "0"))

    def is_admin(message: Message) -> bool:
        return message.from_user is not None and message.from_user.id == admin_id

    @router.message(Command("start"))
    async def cmd_start(message: Message):
        if not is_admin(message):
            await message.answer("Access denied.")
            return
        await message.answer(
            "Jarvis-Omega Online\n"
            "Commands:\n"
            "/status — system metrics\n"
            "/pause — pause workers\n"
            "/resume — resume workers"
        )

    @router.message(Command("status"))
    async def cmd_status(message: Message):
        if not is_admin(message):
            await message.answer("Access denied.")
            return
        metrics = await brain.get_metrics()
        text = (
            f"System Status\n"
            f"Uptime: {metrics['uptime_seconds']}s\n"
            f"Provider: {metrics['active_provider']}\n"
            f"Provider switches: {metrics['provider_switches']}\n"
            f"Requests total: {metrics['requests_total']}\n"
            f"Success rate: {metrics['success_rate']}%\n"
            f"Failed: {metrics['requests_failed']}\n"
            f"Workers paused: {metrics['workers_paused']}\n"
            f"Profit: ${metrics['profit_usd']:.2f}"
        )
        await message.answer(text)

    @router.message(Command("pause"))
    async def cmd_pause(message: Message):
        if not is_admin(message):
            await message.answer("Access denied.")
            return
        await brain.pause_workers()
        await message.answer("Workers paused.")
        logger.info(f"[Admin] Workers paused by admin {admin_id}")

    @router.message(Command("resume"))
    async def cmd_resume(message: Message):
        if not is_admin(message):
            await message.answer("Access denied.")
            return
        await brain.resume_workers()
        await message.answer("Workers resumed.")
        logger.info(f"[Admin] Workers resumed by admin {admin_id}")

    return router


async def start_bot(brain):
    from aiogram import Bot, Dispatcher

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment.")

    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(create_admin_router(brain))

    logger.info("[Admin] Starting Telegram bot polling...")
    await dp.start_polling(bot)
