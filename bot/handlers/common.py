from __future__ import annotations

from aiogram import Dispatcher, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from bot.keyboards.survey import mood_keyboard
from bot.services.survey_service import SurveyService
from bot.services.user_service import UserService


def register(dp: Dispatcher, user_service: UserService, survey_service: SurveyService, admin_id: int) -> None:
    router = Router()

    @router.message(Command("start"))
    async def start_handler(message: Message) -> None:
        if message.from_user is None:
            return
        await user_service.register(message.from_user.id, message.from_user.username)
        await message.answer(
            "Привет! Я бот ежедневного опроса.\n"
            "Каждый день в 20:00 по вашему часовому поясу я пришлю опрос.\n"
            "Установить таймзону: /timezone Europe/Moscow\n"
            "Запустить опрос сейчас: /result\n"
            "Проверка бота: /test"
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

    @router.message(Command("result"))
    async def result_handler(message: Message) -> None:
        if message.from_user is None:
            return

        await user_service.register(message.from_user.id, message.from_user.username)
        survey_id = await survey_service.get_or_create_today_survey_for_user(message.from_user.id)
        if survey_id is None:
            await message.answer("Опрос за сегодня уже завершен ✅")
            return

        await message.answer("Запускаю досрочный опрос.")
        await message.answer("1) Настроение", reply_markup=mood_keyboard(survey_id))

    @router.message(Command("test"))
    async def test_handler(message: Message) -> None:
        if message.from_user is None:
            return

        await user_service.register(message.from_user.id, message.from_user.username)
        await message.answer("Тестовая команда выполнена ✅")
        await message.answer("Тест: запускаю отдельный тестовый опрос (не влияет на /result).")
        await message.answer("1) Настроение", reply_markup=mood_keyboard("test"))

    @router.message(Command("remove_user"))
    async def remove_user_handler(message: Message, command: CommandObject) -> None:
        if message.from_user is None:
            return
        if message.from_user.id != admin_id:
            await message.answer("Команда доступна только администратору.")
            return

        user_id_raw = (command.args or "").strip()
        if not user_id_raw.isdigit():
            await message.answer("Использование: /remove_user <telegram_user_id>")
            return

        removed = await user_service.remove_user(int(user_id_raw))
        if not removed:
            await message.answer("Пользователь не найден в базе.")
            return

        await message.answer(f"Пользователь {user_id_raw} удален. Бот больше не будет ему писать.")

    dp.include_router(router)
