from __future__ import annotations

from aiogram import Dispatcher, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.survey import confirm_keyboard, mode_keyboard
from bot.services.survey_service import SurveyService
from bot.utils.states import SurveyState


def _draft_text(data: dict[str, object]) -> str:
    return (
        "<b>Проверьте анкету перед отправкой</b>\n\n"
        f"1) Настроение: <b>{data['mood']}</b>\n"
        f"2) Режим: <b>{data['mode']}</b>\n"
        f"3) Компаний: <b>{int(data['campaigns'])}</b>\n"
        f"4) Гео: <b>{int(data['geo'])}</b>\n"
        f"5) Подходов по крео: <b>{int(data['creatives'])}</b>\n"
        f"6) Кабинетов: <b>{int(data['accounts'])}</b>\n\n"
        "Если все верно — подтвердите отправку."
    )


def register(dp: Dispatcher, survey_service: SurveyService) -> None:
    router = Router()

    @router.callback_query(F.data.startswith("mood:"))
    async def mood_selected(callback: CallbackQuery, state: FSMContext) -> None:
        if callback.data is None or callback.message is None:
            return
        _, survey_id_raw, mood = callback.data.split(":", maxsplit=2)
        is_test = survey_id_raw == "test"
        await state.clear()
        if is_test:
            await state.update_data(is_test=True, mood=mood)
        else:
            await state.update_data(survey_id=int(survey_id_raw), is_test=False, mood=mood)
        await state.set_state(SurveyState.mode)
        await callback.message.answer("2) Твой режим, масштабирование или тест ?", reply_markup=mode_keyboard(survey_id_raw))
        await callback.answer()

    @router.callback_query(F.data.startswith("mode:"), SurveyState.mode)
    async def mode_selected(callback: CallbackQuery, state: FSMContext) -> None:
        if callback.data is None or callback.message is None:
            return
        _, _, mode = callback.data.split(":", maxsplit=2)
        await state.update_data(mode=mode)
        await state.set_state(SurveyState.campaigns)
        await callback.message.answer("3) Сколько компаний запустил?")
        await callback.answer()

    @router.message(SurveyState.campaigns)
    async def campaigns_handler(message: Message, state: FSMContext) -> None:
        if message.text is None or not message.text.isdigit():
            await message.answer("Введите целое число")
            return
        await state.update_data(campaigns=int(message.text))
        await state.set_state(SurveyState.geo)
        await message.answer("4) Сколько гео запустил?")

    @router.message(SurveyState.geo)
    async def geo_handler(message: Message, state: FSMContext) -> None:
        if message.text is None or not message.text.isdigit():
            await message.answer("Введите целое число")
            return
        await state.update_data(geo=int(message.text))
        await state.set_state(SurveyState.creatives)
        await message.answer("5) Подходы по крео?")

    @router.message(SurveyState.creatives)
    async def creatives_handler(message: Message, state: FSMContext) -> None:
        if message.text is None or not message.text.isdigit():
            await message.answer("Введите целое число")
            return
        await state.update_data(creatives=int(message.text))
        await state.set_state(SurveyState.accounts)
        await message.answer("6) Сколько кабинетов?")

    @router.message(SurveyState.accounts)
    async def accounts_handler(message: Message, state: FSMContext) -> None:
        if message.text is None or not message.text.isdigit():
            await message.answer("Введите целое число")
            return

        await state.update_data(accounts=int(message.text))
        data = await state.get_data()
        await state.set_state(SurveyState.confirm)
        await message.answer(_draft_text(data), reply_markup=confirm_keyboard())

    @router.callback_query(F.data == "survey_confirm:restart", SurveyState.confirm)
    async def restart_survey(callback: CallbackQuery, state: FSMContext) -> None:
        if callback.message is None:
            return

        data = await state.get_data()
        survey_id = data.get("survey_id", "test" if data.get("is_test") else "")
        mood = data.get("mood")

        await state.clear()
        if mood is None:
            await callback.message.answer("Не удалось восстановить анкету. Начните заново командой /result или /test")
            await callback.answer()
            return

        if survey_id == "":
            await callback.message.answer("Не удалось восстановить анкету. Начните заново командой /result или /test")
            await callback.answer()
            return

        is_test = survey_id == "test"
        if is_test:
            await state.update_data(is_test=True, mood=mood, mode=data.get("mode", "Тест"))
        else:
            await state.update_data(survey_id=int(survey_id), is_test=False, mood=mood, mode=data.get("mode", "Масштабирование"))

        await state.set_state(SurveyState.campaigns)
        await callback.message.answer("Заполняем анкету заново.\n3) Сколько компаний запустил?")
        await callback.answer("Ок, начинаем заново")

    @router.callback_query(F.data == "survey_confirm:submit", SurveyState.confirm)
    async def submit_survey(callback: CallbackQuery, state: FSMContext) -> None:
        if callback.message is None:
            return

        data = await state.get_data()
        is_test = bool(data.get("is_test"))
        survey_id = data.get("survey_id")

        if not is_test and survey_id is None:
            await state.clear()
            await callback.message.answer("Не удалось завершить опрос. Попробуйте позже.")
            await callback.answer()
            return

        if is_test:
            score = survey_service.calculate_score(
                mood=str(data["mood"]),
                campaigns=int(data["campaigns"]),
                geo=int(data["geo"]),
                creatives=int(data["creatives"]),
                accounts=int(data["accounts"]),
            )
            await state.clear()
            await callback.message.answer(
                "<b>Тестовый опрос завершен</b> ✅\n\n"
                f"Настроение: <b>{data['mood']}</b>\n"
                f"Режим: <b>{data['mode']}</b>\n"
                f"Компании: <b>{int(data['campaigns'])}</b>\n"
                f"Гео: <b>{int(data['geo'])}</b>\n"
                f"Крео: <b>{int(data['creatives'])}</b>\n"
                f"Кабинеты: <b>{int(data['accounts'])}</b>\n\n"
                f"Итог: <b>{score.final_color} ({score.average:.2f})</b>\n"
                f"{score.message}\n\n"
                "<i>Это тестовый результат — он не сохранен в БД и не влияет на /result.</i>"
            )
            await callback.answer("Отправлено")
            return

        result = await survey_service.complete_survey(
            survey_id=int(survey_id),
            mood=str(data["mood"]),
            campaigns=int(data["campaigns"]),
            geo=int(data["geo"]),
            creatives=int(data["creatives"]),
            accounts=int(data["accounts"]),
        )
        await state.clear()
        if result is None:
            await callback.message.answer("Этот опрос уже закрыт.")
            await callback.answer()
            return

        full = await survey_service.get_full_survey(int(survey_id))
        if full is None or full.answer is None:
            await callback.message.answer("Ошибка получения результатов.")
            await callback.answer()
            return

        score = result.score
        await callback.message.answer(
            "<b>Опрос завершен!</b>\n\n"
            f"Настроение: <b>{full.answer.mood}</b>\n"
            f"Режим: <b>{data['mode']}</b>\n"
            f"Компании: <b>{full.answer.campaigns_count}</b>\n"
            f"Гео: <b>{full.answer.geo_count}</b>\n"
            f"Крео: <b>{full.answer.creatives_count}</b>\n"
            f"Кабинеты: <b>{full.answer.accounts_count}</b>\n\n"
            f"Итог: <b>{score.final_color} ({score.average:.2f})</b>\n"
            f"{score.message}"
        )

        report_text = (
            "<b>📊 Daily Survey Report</b>\n"
            f"🗓 Дата: <b>{full.date.isoformat()}</b>\n"
            f"👤 Пользователь: <b>@{full.user.username if full.user and full.user.username else '-'}</b>\n"
            f"🆔 user_id: <code>{full.user.user_id if full.user else '-'}</code>\n\n"
            "<b>Ответы</b>\n"
            f"• Настроение: {full.answer.mood}\n"
            f"• Режим: {data['mode']}\n"
            f"• Компании: {full.answer.campaigns_count} → {score.campaigns_color}\n"
            f"• Гео: {full.answer.geo_count} → {score.geo_color}\n"
            f"• Крео: {full.answer.creatives_count} → {score.creatives_color}\n"
            f"• Кабинеты: {full.answer.accounts_count} → {score.accounts_color}\n\n"
            f"<b>Итог:</b> {score.final_color} <b>({score.average:.2f})</b>\n"
            f"💬 {score.message}"
        )
        for target in survey_service.report_targets:
            await callback.message.bot.send_message(chat_id=target, text=report_text)

        await callback.answer("Анкета отправлена")

    dp.include_router(router)
