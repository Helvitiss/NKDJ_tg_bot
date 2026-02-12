from aiogram.fsm.state import State, StatesGroup


class SurveyState(StatesGroup):
    mood = State()
    mode = State()
    campaigns = State()
    geo = State()
    creatives = State()
    accounts = State()
    confirm = State()
