from aiogram.fsm.state import State, StatesGroup


class ContactStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()


class ServiceStates(StatesGroup):
    add_name = State()
    add_description = State()
    add_duration = State()
    add_price = State()
    edit_price = State()


class SettingsStates(StatesGroup):
    shop_name = State()
    address = State()
    barber_name = State()


class ScheduleStates(StatesGroup):
    working_hours = State()
    break_time = State()
    off_days = State()
    blocked_slot = State()


class RescheduleStates(StatesGroup):
    date = State()
    time = State()


class BarberApplicationStates(StatesGroup):
    specialty = State()
    experience = State()
    phone = State()
    photo = State()
