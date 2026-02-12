from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from zoneinfo import ZoneInfo

from bot.db.models import Survey
from bot.domain.scoring import ScoringEngine, ScoreResult
from bot.repositories.surveys import SurveyRepository
from bot.repositories.users import UserRepository


@dataclass(slots=True)
class CompletionResult:
    survey_id: int
    score: ScoreResult
    completed_at: datetime


class SurveyService:
    def __init__(self, session_factory: async_sessionmaker, admin_id: int, report_chat_id: int | None = None) -> None:
        self.session_factory = session_factory
        self.scoring_engine = ScoringEngine()
        self.admin_id = admin_id
        self.report_chat_id = report_chat_id

    @property
    def report_targets(self) -> list[int]:
        if self.report_chat_id is None or self.report_chat_id == self.admin_id:
            return [self.admin_id]
        return [self.admin_id, self.report_chat_id]

    async def complete_survey(
        self,
        survey_id: int,
        mood: str,
        campaigns: int,
        geo: int,
        creatives: int,
        accounts: int,
    ) -> CompletionResult | None:
        async with self.session_factory() as session:
            repo = SurveyRepository(session)
            async with session.begin():
                survey = await repo.get_pending_by_id(survey_id)
                if survey is None:
                    return None
                score = self.scoring_engine.score(mood, campaigns, geo, creatives, accounts)
                updated = await repo.save_answer(survey, mood, campaigns, geo, creatives, accounts)
                completed_at = updated.completed_at or datetime.utcnow()
                return CompletionResult(survey_id=updated.id, score=score, completed_at=completed_at)

    async def get_full_survey(self, survey_id: int) -> Survey | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(Survey)
                .options(selectinload(Survey.user), selectinload(Survey.answer))
                .where(Survey.id == survey_id)
            )
            return result.scalar_one_or_none()

    async def get_or_create_today_survey_for_user(self, telegram_user_id: int) -> int | None:
        async with self.session_factory() as session:
            user_repo = UserRepository(session)
            survey_repo = SurveyRepository(session)

            async with session.begin():
                user = await user_repo.get_by_telegram_id(telegram_user_id)
                if user is None:
                    return None

                local_now = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(user.timezone))
                survey, _ = await survey_repo.create_daily_if_absent(user=user, survey_date=local_now.date())
                if survey.status.value != "pending":
                    return None

                return survey.id
