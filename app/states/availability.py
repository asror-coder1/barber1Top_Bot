from aiogram.fsm.state import State, StatesGroup


class AvailabilityStates(StatesGroup):
    barber = State()
    date = State()
