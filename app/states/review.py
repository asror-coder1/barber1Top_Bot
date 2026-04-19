from aiogram.fsm.state import State, StatesGroup


class ReviewStates(StatesGroup):
    rating = State()
    comment = State()
