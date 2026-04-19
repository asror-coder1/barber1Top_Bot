from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.constants import (
    AI_RECOMMENDATION,
    BECOME_BARBER,
    BOOK_APPOINTMENT,
    BONUSES,
    CHOOSE_BARBER,
    FREE_SLOTS,
    LOCATION,
    PRICES,
    REVIEW,
)


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BOOK_APPOINTMENT), KeyboardButton(text=CHOOSE_BARBER)],
            [KeyboardButton(text=FREE_SLOTS), KeyboardButton(text=PRICES)],
            [KeyboardButton(text=AI_RECOMMENDATION), KeyboardButton(text=BONUSES)],
            [KeyboardButton(text=LOCATION), KeyboardButton(text=REVIEW)],
            [KeyboardButton(text=BECOME_BARBER)],
        ],
        resize_keyboard=True,
    )


def phone_request_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon ulashish", request_contact=True)],
            [KeyboardButton(text="O'tkazib yuborish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def registration_phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon ulashish", request_contact=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="+998 90 123 45 67",
    )


def barber_panel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Mening bronlarim"), KeyboardButton(text="📈 Dashboard")],
            [KeyboardButton(text="🕒 Mening jadvalim"), KeyboardButton(text="👤 Mening profilim")],
            [KeyboardButton(text="⚙️ Sozlamalar")],
        ],
        resize_keyboard=True,
    )
