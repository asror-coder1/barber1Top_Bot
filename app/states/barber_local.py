from aiogram.fsm.state import State, StatesGroup


class LocalBarberSettingsStates(StatesGroup):
    working_hours = State()
    break_time = State()
    off_days = State()
    specialty = State()
    phone = State()
    bio = State()
