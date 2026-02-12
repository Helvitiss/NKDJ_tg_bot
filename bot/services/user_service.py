from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.repositories.users import UserRepository
from bot.utils.timezone import normalize_timezone_input


class UserService:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.session_factory = session_factory

    async def register(self, telegram_user_id: int, username: str | None) -> None:
        async with self.session_factory() as session:
            repo = UserRepository(session)
            async with session.begin():
                await repo.create_or_update(telegram_user_id, username)

    async def set_timezone(self, telegram_user_id: int, timezone: str) -> str | None:
        normalized_timezone = normalize_timezone_input(timezone)
        if normalized_timezone is None:
            return None

        async with self.session_factory() as session:
            repo = UserRepository(session)
            async with session.begin():
                await repo.set_timezone(telegram_user_id, normalized_timezone)
        return normalized_timezone

    async def remove_user(self, telegram_user_id: int) -> bool:
        async with self.session_factory() as session:
            repo = UserRepository(session)
            async with session.begin():
                return await repo.delete_by_telegram_id(telegram_user_id)
