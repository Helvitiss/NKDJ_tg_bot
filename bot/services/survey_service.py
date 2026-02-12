from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload

from bot.db.models import Survey
from bot.domain.scoring import ScoringEngine, ScoreResult
from bot.repositories.surveys import SurveyRepository
from bot.repositories.users import UserRepository
from bot.utils.timezone import local_now_from_timezone


@dataclass(slots=True)
class CompletionResult:
    survey_id: int
    score: ScoreResult
    completed_at: datetime


@dataclass(slots=True)
class StatsEntry:
    username: str
    user_id: int
    surveys_count: int
    mood_avg: float
    campaigns_avg: float
    geo_avg: float
    creatives_avg: float
    accounts_avg: float
    score_avg: float


@dataclass(slots=True)
class StatsReport:
    period: str
    date_from: date
    date_to: date
    per_user: list[StatsEntry]
    overall: StatsEntry | None


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

    def calculate_score(
        self,
        mood: str,
        campaigns: int,
        geo: int,
        creatives: int,
        accounts: int,
    ) -> ScoreResult:
        return self.scoring_engine.score(mood, campaigns, geo, creatives, accounts)

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

                local_now = local_now_from_timezone(user.timezone)
                survey, _ = await survey_repo.create_daily_if_absent(user_db_id=user.id, survey_date=local_now.date())
                if survey.status.value != "pending":
                    return None

                return survey.id

    async def collect_stats(self, period: str) -> StatsReport:
        days = {"day": 1, "week": 7, "month": 30}.get(period, 1)
        date_to = datetime.utcnow().date()
        date_from = date_to - timedelta(days=days - 1)

        async with self.session_factory() as session:
            repo = SurveyRepository(session)
            surveys = await repo.list_answered_in_range(date_from, date_to)

        grouped: dict[int, list[Survey]] = {}
        for survey in surveys:
            if survey.user is None or survey.answer is None:
                continue
            grouped.setdefault(survey.user.user_id, []).append(survey)

        entries: list[StatsEntry] = []
        for user_id, user_surveys in grouped.items():
            entries.append(self._build_stats_entry(user_surveys, user_id=user_id))

        entries.sort(key=lambda x: x.user_id)
        overall = self._build_stats_entry(surveys, user_id=0, username_override="Общая статистика") if surveys else None

        return StatsReport(
            period=period,
            date_from=date_from,
            date_to=date_to,
            per_user=entries,
            overall=overall,
        )

    def _build_stats_entry(
        self,
        surveys: list[Survey],
        user_id: int,
        username_override: str | None = None,
    ) -> StatsEntry:
        answers = [s.answer for s in surveys if s.answer is not None]
        if not answers:
            return StatsEntry(
                username=username_override or "-",
                user_id=user_id,
                surveys_count=0,
                mood_avg=0.0,
                campaigns_avg=0.0,
                geo_avg=0.0,
                creatives_avg=0.0,
                accounts_avg=0.0,
                score_avg=0.0,
            )

        mood_map = {"🟢": 2.0, "🟡": 1.0, "🔴": 0.0}
        mood_avg = sum(mood_map.get(a.mood, 0.0) for a in answers) / len(answers)
        campaigns_avg = sum(a.campaigns_count for a in answers) / len(answers)
        geo_avg = sum(a.geo_count for a in answers) / len(answers)
        creatives_avg = sum(a.creatives_count for a in answers) / len(answers)
        accounts_avg = sum(a.accounts_count for a in answers) / len(answers)

        score_values = [
            self.scoring_engine.score(a.mood, a.campaigns_count, a.geo_count, a.creatives_count, a.accounts_count).average
            for a in answers
        ]
        score_avg = sum(score_values) / len(score_values)

        first_with_user = next((s for s in surveys if s.user is not None), None)
        username = username_override
        if username is None:
            if first_with_user is None:
                username = "-"
            else:
                username = first_with_user.user.username or "-"

        return StatsEntry(
            username=username,
            user_id=user_id,
            surveys_count=len(answers),
            mood_avg=mood_avg,
            campaigns_avg=campaigns_avg,
            geo_avg=geo_avg,
            creatives_avg=creatives_avg,
            accounts_avg=accounts_avg,
            score_avg=score_avg,
        )
