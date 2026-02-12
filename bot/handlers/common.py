from __future__ import annotations

from aiogram import Dispatcher, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from bot.services.user_service import UserService


def register(dp: Dispatcher, user_service: UserService) -> None:
    router = Router()

    @router.message(Command("start"))
    async def start_handler(message: Message) -> None:
        if message.from_user is None:
            return
        await user_service.register(message.from_user.id, message.from_user.username)
        await message.answer(
            "Привет! Я бот ежедневного опроса.\n"
            "Каждый день в 20:00 по вашему часовому поясу я пришлю опрос.\n"
            "Установить таймзону: /timezone Europe/Moscow"
        )

    @router.message(Command("timezone"))
    async def timezone_handler(message: Message, command: CommandObject) -> None:
        if message.from_user is None:
            return
        timezone = (command.args or "").strip()
        if not timezone:
            await message.answer("Укажите таймзону, например: /timezone Europe/Moscow")
            return
        ok = await user_service.set_timezone(message.from_user.id, timezone)
        if not ok:
            await message.answer("Некорректная таймзона. Используйте IANA формат, например Europe/Moscow")
            return
        await message.answer(f"Таймзона обновлена: {timezone}")

    dp.include_router(router)
