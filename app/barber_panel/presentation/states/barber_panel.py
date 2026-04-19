from aiogram.fsm.state import State, StatesGroup


class ProfileStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_profile_photo = State()
    waiting_for_portfolio_photo = State()


class ServiceStates(StatesGroup):
    add_name = State()
    add_description = State()
    add_duration = State()
    add_price = State()
    edit_value = State()
    bulk_price = State()


class ScheduleStates(StatesGroup):
    waiting_for_hours = State()
    waiting_for_break = State()
    waiting_for_unavailable_date = State()
    waiting_for_custom_open_slot = State()
    waiting_for_custom_closed_slot = State()


class ReviewStates(StatesGroup):
    waiting_for_reply = State()


class ChatStates(StatesGroup):
    waiting_for_reply = State()


class BookingStates(StatesGroup):
    waiting_for_reschedule_date = State()
    waiting_for_reschedule_time = State()

