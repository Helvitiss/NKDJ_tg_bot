from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def mood_keyboard(survey_id: int | str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢", callback_data=f"mood:{survey_id}:🟢"),
                InlineKeyboardButton(text="🟡", callback_data=f"mood:{survey_id}:🟡"),
                InlineKeyboardButton(text="🔴", callback_data=f"mood:{survey_id}:🔴"),
            ]
        ]
    )


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="survey_confirm:submit"),
                InlineKeyboardButton(text="✏️ Заполнить заново", callback_data="survey_confirm:restart"),
            ]
        ]
    )
