from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, timezone

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.keyboards.survey import mood_keyboard
from bot.repositories.surveys import SurveyRepository
from bot.repositories.users import UserRepository
from bot.utils.timezone import tzinfo_from_stored

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self, bot: Bot, session_factory: async_sessionmaker, admin_id: int, report_chat_id: int | None = None) -> None:
        self.bot = bot
        self.session_factory = session_factory
        self.admin_id = admin_id
        self.report_chat_id = report_chat_id
        self.scheduler = AsyncIOScheduler(timezone="UTC")

    @property
    def report_targets(self) -> list[int]:
        if self.report_chat_id is None or self.report_chat_id == self.admin_id:
            return [self.admin_id]
        return [self.admin_id, self.report_chat_id]

    def start(self) -> None:
        self.scheduler.add_job(self.sync_deferred_survey_jobs, "interval", minutes=10, id="sync_deferred_surveys", replace_existing=True)
        self.scheduler.add_job(self.notify_overdue_surveys, "interval", minutes=30, id="overdue_notify", replace_existing=True)
        self.scheduler.start()
        # Первая синхронизация сразу после старта.
        self.scheduler.add_job(self.sync_deferred_survey_jobs, "date", run_date=datetime.now(tz=timezone.utc) + timedelta(seconds=1))

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    async def sync_deferred_survey_jobs(self) -> None:
        now_utc = datetime.now(tz=timezone.utc)
        async with self.session_factory() as session:
            user_repo = UserRepository(session)
            users = await user_repo.list_all()

        for user in users:
            target_local_date, run_at_utc = self._next_run_for_user(user.timezone, now_utc)
            job_id = self._job_id(user.user_id, target_local_date)
            if self.scheduler.get_job(job_id) is not None:
                continue

            self.scheduler.add_job(
                self.send_daily_survey_job,
                "date",
                run_date=run_at_utc,
                id=job_id,
                kwargs={
                    "telegram_user_id": user.user_id,
                    "user_db_id": user.id,
                    "survey_date": target_local_date.isoformat(),
                },
                replace_existing=True,
            )
            logger.info(
                "Scheduled deferred survey job_id=%s user_id=%s at=%s",
                job_id,
                user.user_id,
                run_at_utc.isoformat(),
            )

    async def send_daily_survey_job(self, telegram_user_id: int, user_db_id: int, survey_date: str) -> None:
        target_date = date.fromisoformat(survey_date)
        async with self.session_factory() as session:
            survey_repo = SurveyRepository(session)
            async with session.begin():
                survey, created = await survey_repo.create_daily_if_absent(user_db_id=user_db_id, survey_date=target_date)
                if not created:
                    logger.info("Skip deferred send for user_id=%s date=%s (survey already exists)", telegram_user_id, target_date)
                    return

            await self.bot.send_message(chat_id=telegram_user_id, text="1) Настроение", reply_markup=mood_keyboard(survey.id))
            logger.info("Deferred survey sent to user_id=%s survey_id=%s", telegram_user_id, survey.id)

    async def notify_overdue_surveys(self) -> None:
        async with self.session_factory() as session:
            repo = SurveyRepository(session)
            async with session.begin():
                surveys = await repo.pending_overdue_without_admin_notification()
                for survey in surveys:
                    overdue_text = (
                        "<b>⏰ Нет ответа на daily survey более 12 часов</b>\n"
                        f"🗓 Дата: <b>{survey.date.isoformat()}</b>\n"
                        f"👤 Пользователь: <b>@{survey.user.username if survey.user and survey.user.username else '-'}</b>\n"
                        f"🆔 user_id: <code>{survey.user.user_id if survey.user else '-'}</code>"
                    )
                    for target in self.report_targets:
                        await self.bot.send_message(chat_id=target, text=overdue_text)
                    await repo.mark_admin_notified(survey)

    @staticmethod
    def _job_id(telegram_user_id: int, survey_date: date) -> str:
        return f"deferred_survey:{telegram_user_id}:{survey_date.isoformat()}"

    @staticmethod
    def _next_run_for_user(user_timezone: str, now_utc: datetime) -> tuple[date, datetime]:
        tz = tzinfo_from_stored(user_timezone)
        now_local = now_utc.astimezone(tz)
        today_target_local = datetime.combine(now_local.date(), time(hour=20, minute=0), tzinfo=tz)

        if now_local < today_target_local:
            target_local = today_target_local
        else:
            tomorrow = now_local.date() + timedelta(days=1)
            target_local = datetime.combine(tomorrow, time(hour=20, minute=0), tzinfo=tz)

        return target_local.date(), target_local.astimezone(timezone.utc)
