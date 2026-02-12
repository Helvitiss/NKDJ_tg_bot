from __future__ import annotations

from aiogram import Dispatcher, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.services.survey_service import SurveyService
from bot.utils.states import SurveyState


def register(dp: Dispatcher, survey_service: SurveyService) -> None:
    router = Router()

    @router.callback_query(F.data.startswith("mood:"))
    async def mood_selected(callback: CallbackQuery, state: FSMContext) -> None:
        if callback.data is None or callback.message is None:
            return
        _, survey_id_raw, mood = callback.data.split(":", maxsplit=2)
        await state.clear()
        await state.update_data(survey_id=int(survey_id_raw), mood=mood)
        await state.set_state(SurveyState.campaigns)
        await callback.message.answer("2) Сколько компаний запустил?")
        await callback.answer()

    @router.message(SurveyState.campaigns)
    async def campaigns_handler(message: Message, state: FSMContext) -> None:
        if message.text is None or not message.text.isdigit():
            await message.answer("Введите целое число")
            return
        await state.update_data(campaigns=int(message.text))
        await state.set_state(SurveyState.geo)
        await message.answer("3) Сколько гео запустил?")

    @router.message(SurveyState.geo)
    async def geo_handler(message: Message, state: FSMContext) -> None:
        if message.text is None or not message.text.isdigit():
            await message.answer("Введите целое число")
            return
        await state.update_data(geo=int(message.text))
        await state.set_state(SurveyState.creatives)
        await message.answer("4) Подходы по крео?")

    @router.message(SurveyState.creatives)
    async def creatives_handler(message: Message, state: FSMContext) -> None:
        if message.text is None or not message.text.isdigit():
            await message.answer("Введите целое число")
            return
        await state.update_data(creatives=int(message.text))
        await state.set_state(SurveyState.accounts)
        await message.answer("5) Сколько кабинетов?")

    @router.message(SurveyState.accounts)
    async def accounts_handler(message: Message, state: FSMContext) -> None:
        if message.text is None or not message.text.isdigit():
            await message.answer("Введите целое число")
            return
        data = await state.get_data()
        survey_id = data.get("survey_id")
        if survey_id is None:
            await state.clear()
            await message.answer("Не удалось завершить опрос. Попробуйте позже.")
            return

        result = await survey_service.complete_survey(
            survey_id=survey_id,
            mood=str(data["mood"]),
            campaigns=int(data["campaigns"]),
            geo=int(data["geo"]),
            creatives=int(data["creatives"]),
            accounts=int(message.text),
        )
        await state.clear()
        if result is None:
            await message.answer("Этот опрос уже закрыт.")
            return

        full = await survey_service.get_full_survey(survey_id)
        if full is None or full.answer is None:
            await message.answer("Ошибка получения результатов.")
            return

        score = result.score
        await message.answer(
            "Опрос завершен!\n"
            f"Настроение: {full.answer.mood}\n"
            f"Компании: {full.answer.campaigns_count}\n"
            f"Гео: {full.answer.geo_count}\n"
            f"Крео: {full.answer.creatives_count}\n"
            f"Кабинеты: {full.answer.accounts_count}\n\n"
            f"Итог: {score.final_color} ({score.average:.2f})\n"
            f"{score.message}"
        )

        report_text = (
            "Новый завершенный daily survey\n"
            f"username: @{full.user.username if full.user and full.user.username else '-'}\n"
            f"user_id: {full.user.user_id if full.user else '-'}\n"
            f"date: {full.date.isoformat()}\n"
            f"raw: mood={full.answer.mood}, campaigns={full.answer.campaigns_count}, "
            f"geo={full.answer.geo_count}, creatives={full.answer.creatives_count}, "
            f"accounts={full.answer.accounts_count}\n"
            f"colors: mood={score.mood_color}, campaigns={score.campaigns_color}, geo={score.geo_color}, "
            f"creatives={score.creatives_color}, accounts={score.accounts_color}\n"
            f"total: {score.final_color} ({score.average:.2f}) {score.message}"
        )
        for target in survey_service.report_targets:
            await message.bot.send_message(chat_id=target, text=report_text)

    dp.include_router(router)
