from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    service = State()
    barber = State()
    date = State()
    time = State()
    confirm = State()
