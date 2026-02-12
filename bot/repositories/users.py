from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_user_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.user_id == telegram_user_id))
        return result.scalar_one_or_none()

    async def create_or_update(self, telegram_user_id: int, username: str | None) -> User:
        user = await self.get_by_telegram_id(telegram_user_id)
        if user is None:
            user = User(user_id=telegram_user_id, username=username)
            self.session.add(user)
        else:
            user.username = username
        await self.session.flush()
        return user

    async def set_timezone(self, telegram_user_id: int, timezone: str) -> None:
        user = await self.get_by_telegram_id(telegram_user_id)
        if user is not None:
            user.timezone = timezone
            await self.session.flush()

    async def list_all(self) -> list[User]:
        result = await self.session.execute(select(User))
        return list(result.scalars().all())

    async def delete_by_telegram_id(self, telegram_user_id: int) -> bool:
        result = await self.session.execute(delete(User).where(User.user_id == telegram_user_id))
        await self.session.flush()
        return bool(result.rowcount)
