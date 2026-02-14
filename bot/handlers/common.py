from __future__ import annotations

from aiogram import Dispatcher, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from bot.keyboards.survey import mood_keyboard
from bot.services.survey_service import StatsEntry, SurveyService
from bot.services.user_service import UserService


def _format_stats_entry(entry: StatsEntry) -> str:
    return (
        f"👤 <b>@{entry.username}</b> (<code>{entry.user_id}</code>)\n"
        f"• Анкет: <b>{entry.surveys_count}</b>\n"
        f"• Настроение (avg): <b>{entry.mood_avg:.2f}</b>\n"
        f"• Компании (avg): <b>{entry.campaigns_avg:.2f}</b>\n"
        f"• Гео (avg): <b>{entry.geo_avg:.2f}</b>\n"
        f"• Крео (avg): <b>{entry.creatives_avg:.2f}</b>\n"
        f"• Кабинеты (avg): <b>{entry.accounts_avg:.2f}</b>\n"
        f"• Эффективность (avg): <b>{entry.score_avg:.2f}</b>"
    )


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
            "Установить таймзону: /timezone Europe/Warsaw или /timezone +1\n"
            "Запустить опрос сейчас: /result\n"
            "Проверка бота: /test"
        )

    @router.message(Command("timezone"))
    async def timezone_handler(message: Message, command: CommandObject) -> None:
        if message.from_user is None:
            return
        timezone = (command.args or "").strip()
        if not timezone:
            await message.answer(
                "Укажите таймзону. Примеры:\n"
                "• /timezone Europe/Warsaw\n"
                "• /timezone +1\n"
                "• /timezone -2"
            )
            return
        normalized_timezone = await user_service.set_timezone(message.from_user.id, timezone)
        if normalized_timezone is None:
            await message.answer(
                "Некорректная таймзона. Используйте IANA (Europe/Warsaw) "
                "или смещение UTC в формате +1 / -2"
            )
            return
        await message.answer(f"Таймзона обновлена: <b>{normalized_timezone}</b>")

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

    @router.message(Command("stats"))
    async def stats_handler(message: Message, command: CommandObject) -> None:
        if message.from_user is None:
            return
        if message.from_user.id != admin_id:
            await message.answer("Команда /stats доступна только администратору.")
            return

        period = (command.args or "day").strip().lower()
        if period not in {"day", "week", "month"}:
            await message.answer("Использование: /stats [day|week|month]")
            return

        report = await survey_service.collect_stats(period)
        if not report.per_user:
            await message.answer(
                f"📈 Статистика за <b>{period}</b> ({report.date_from} — {report.date_to})\n\n"
                "Нет завершенных анкет за выбранный период."
            )
            return

        blocks = [
            f"📈 <b>Статистика за {period}</b>\n"
            f"Период: <b>{report.date_from}</b> — <b>{report.date_to}</b>\n"
        ]
        for entry in report.per_user:
            blocks.append(_format_stats_entry(entry))

        if report.overall is not None:
            overall = report.overall
            blocks.append(
                "🌐 <b>Общая статистика</b>\n"
                f"• Анкет: <b>{overall.surveys_count}</b>\n"
                f"• Настроение (avg): <b>{overall.mood_avg:.2f}</b>\n"
                f"• Компании (avg): <b>{overall.campaigns_avg:.2f}</b>\n"
                f"• Гео (avg): <b>{overall.geo_avg:.2f}</b>\n"
                f"• Крео (avg): <b>{overall.creatives_avg:.2f}</b>\n"
                f"• Кабинеты (avg): <b>{overall.accounts_avg:.2f}</b>\n"
                f"• Эффективность (avg): <b>{overall.score_avg:.2f}</b>"
            )

        await message.answer("\n\n".join(blocks))

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
