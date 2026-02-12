from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.repositories.users import UserRepository


class UserService:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.session_factory = session_factory

    async def register(self, telegram_user_id: int, username: str | None) -> None:
        async with self.session_factory() as session:
            repo = UserRepository(session)
            async with session.begin():
                await repo.create_or_update(telegram_user_id, username)

    async def set_timezone(self, telegram_user_id: int, timezone: str) -> bool:
        try:
            ZoneInfo(timezone)
        except ZoneInfoNotFoundError:
            return False

        async with self.session_factory() as session:
            repo = UserRepository(session)
            async with session.begin():
                await repo.set_timezone(telegram_user_id, timezone)
        return True

    async def remove_user(self, telegram_user_id: int) -> bool:
        async with self.session_factory() as session:
            repo = UserRepository(session)
            async with session.begin():
                return await repo.delete_by_telegram_id(telegram_user_id)
