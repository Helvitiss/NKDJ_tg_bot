from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.db.models import Answer, Survey, SurveyStatus, User


class SurveyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_daily_if_absent(self, user: User, survey_date: date) -> tuple[Survey, bool]:
        survey = Survey(user_id=user.id, date=survey_date)
        self.session.add(survey)
        try:
            await self.session.flush()
            return survey, True
        except IntegrityError:
            await self.session.rollback()
            existing = await self.get_by_user_and_date(user.id, survey_date)
            if existing is None:
                raise
            return existing, False

    async def get_by_user_and_date(self, user_db_id: int, survey_date: date) -> Survey | None:
        result = await self.session.execute(
            select(Survey).where(and_(Survey.user_id == user_db_id, Survey.date == survey_date))
        )
        return result.scalar_one_or_none()

    async def get_pending_by_id(self, survey_id: int) -> Survey | None:
        result = await self.session.execute(
            select(Survey)
            .options(selectinload(Survey.user), selectinload(Survey.answer))
            .where(and_(Survey.id == survey_id, Survey.status == SurveyStatus.pending))
        )
        return result.scalar_one_or_none()

    async def save_answer(
        self,
        survey: Survey,
        mood: str,
        campaigns_count: int,
        geo_count: int,
        creatives_count: int,
        accounts_count: int,
    ) -> Survey:
        survey.answer = Answer(
            mood=mood,
            campaigns_count=campaigns_count,
            geo_count=geo_count,
            creatives_count=creatives_count,
            accounts_count=accounts_count,
        )
        survey.status = SurveyStatus.answered
        survey.completed_at = datetime.utcnow()
        await self.session.flush()
        return survey

    async def pending_overdue_without_admin_notification(self) -> list[Survey]:
        border = datetime.utcnow() - timedelta(hours=12)
        result = await self.session.execute(
            select(Survey)
            .options(selectinload(Survey.user))
            .where(
                and_(
                    Survey.status == SurveyStatus.pending,
                    Survey.sent_at <= border,
                    Survey.admin_notified_at.is_(None),
                )
            )
        )
        return list(result.scalars().all())

    async def mark_admin_notified(self, survey: Survey) -> None:
        survey.admin_notified_at = datetime.utcnow()
        await self.session.flush()
