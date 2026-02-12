from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def mood_keyboard(survey_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢", callback_data=f"mood:{survey_id}:🟢"),
                InlineKeyboardButton(text="🟡", callback_data=f"mood:{survey_id}:🟡"),
                InlineKeyboardButton(text="🔴", callback_data=f"mood:{survey_id}:🔴"),
            ]
        ]
    )
