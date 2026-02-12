from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.repositories.surveys import SurveyRepository
from bot.repositories.users import UserRepository
from bot.keyboards.survey import mood_keyboard


logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self, bot: Bot, session_factory: async_sessionmaker, admin_id: int, report_chat_id: int | None = None) -> None:
        self.bot = bot
        self.session_factory = session_factory
        self.admin_id = admin_id
        self.report_chat_id = report_chat_id
        self.scheduler = AsyncIOScheduler()

    @property
    def report_targets(self) -> list[int]:
        if self.report_chat_id is None or self.report_chat_id == self.admin_id:
            return [self.admin_id]
        return [self.admin_id, self.report_chat_id]

    def start(self) -> None:
        self.scheduler.add_job(self.dispatch_daily_surveys, "interval", minutes=1, id="dispatch_daily", replace_existing=True)
        self.scheduler.add_job(self.notify_overdue_surveys, "interval", minutes=30, id="overdue_notify", replace_existing=True)
        self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    async def dispatch_daily_surveys(self) -> None:
        now_utc = datetime.utcnow()
        async with self.session_factory() as session:
            user_repo = UserRepository(session)
            survey_repo = SurveyRepository(session)
            users = await user_repo.list_all()

            for user in users:
                local_now = now_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(user.timezone))
                if local_now.hour != 20 or local_now.minute != 0:
                    continue

                async with session.begin():
                    survey, created = await survey_repo.create_daily_if_absent(user=user, survey_date=local_now.date())
                    if not created:
                        continue

                await self.bot.send_message(chat_id=user.user_id, text="1) Настроение", reply_markup=mood_keyboard(survey.id))
                logger.info("Survey sent to user_id=%s survey_id=%s", user.user_id, survey.id)

    async def notify_overdue_surveys(self) -> None:
        async with self.session_factory() as session:
            repo = SurveyRepository(session)
            async with session.begin():
                surveys = await repo.pending_overdue_without_admin_notification()
                for survey in surveys:
                    overdue_text = (
                        "Пользователь не ответил в течение 12 часов\n"
                        f"username: @{survey.user.username if survey.user and survey.user.username else '-'}\n"
                        f"user_id: {survey.user.user_id if survey.user else '-'}\n"
                        f"date: {survey.date.isoformat()}"
                    )
                    for target in self.report_targets:
                        await self.bot.send_message(chat_id=target, text=overdue_text)
                    await repo.mark_admin_notified(survey)
