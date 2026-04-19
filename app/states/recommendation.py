from aiogram.fsm.state import State, StatesGroup


class RecommendationStates(StatesGroup):
    photo = State()
    face_shape = State()
    hair_length = State()
    preferred_style = State()
    maintenance = State()
    beard_style = State()
