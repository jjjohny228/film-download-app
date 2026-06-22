from aiogram.fsm.state import State, StatesGroup


class SearchStates(StatesGroup):
    waiting_title = State()
    browsing_results = State()
    selecting_translation = State()
    selecting_season = State()
    selecting_episode = State()
    selecting_quality = State()


class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_proxy = State()
