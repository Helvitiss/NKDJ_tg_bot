from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.db.models import Answer, Survey, SurveyStatus


class SurveyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_daily_if_absent(self, user_db_id: int, survey_date: date) -> tuple[Survey, bool]:
        stmt = (
            insert(Survey)
            .values(user_id=user_db_id, date=survey_date)
            .on_conflict_do_nothing(index_elements=[Survey.user_id, Survey.date])
            .returning(Survey.id)
        )
        inserted_id = await self.session.scalar(stmt)
        if inserted_id is not None:
            created = await self.session.get(Survey, inserted_id)
            if created is None:
                raise RuntimeError("Inserted survey was not found")
            return created, True

        existing = await self.get_by_user_and_date(user_db_id, survey_date)
        if existing is None:
            raise RuntimeError("Survey conflict detected but existing row was not found")
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
