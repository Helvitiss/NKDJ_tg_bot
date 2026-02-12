from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from bot.db.models import Survey
from bot.domain.scoring import ScoringEngine, ScoreResult
from bot.repositories.surveys import SurveyRepository


@dataclass(slots=True)
class CompletionResult:
    survey_id: int
    score: ScoreResult
    completed_at: datetime


class SurveyService:
    def __init__(self, session_factory: async_sessionmaker, admin_id: int) -> None:
        self.session_factory = session_factory
        self.scoring_engine = ScoringEngine()
        self.admin_id = admin_id

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
