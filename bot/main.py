from __future__ import annotations

import asyncio
import logging

from functools import partial

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config.settings import get_settings
from bot.db.base import Base
from bot.db.session import engine, session_factory
from bot.handlers import common, survey
from bot.scheduler.jobs import SchedulerService
from bot.services.survey_service import SurveyService
from bot.services.user_service import UserService


async def on_startup(scheduler_service: SchedulerService) -> None:
    logging.info("Starting up bot...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logging.info("Database schema ready")
    scheduler_service.start()
    logging.info("Scheduler started")


async def on_shutdown(scheduler_service: SchedulerService) -> None:
    logging.info("Shutting down bot...")
    scheduler_service.shutdown()
    await engine.dispose()
    logging.info("Shutdown complete")


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    settings = get_settings()

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    user_service = UserService(session_factory=session_factory)
    survey_service = SurveyService(
        session_factory=session_factory,
        admin_id=settings.admin_id,
        report_chat_id=settings.report_chat_id,
    )
    scheduler_service = SchedulerService(
        bot=bot,
        session_factory=session_factory,
        admin_id=settings.admin_id,
        report_chat_id=settings.report_chat_id,
    )

    common.register(dp, user_service, survey_service, settings.admin_id)
    survey.register(dp, survey_service)

    dp.startup.register(partial(on_startup, scheduler_service))
    dp.shutdown.register(partial(on_shutdown, scheduler_service))

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
