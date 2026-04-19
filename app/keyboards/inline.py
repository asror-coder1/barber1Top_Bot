from __future__ import annotations

from datetime import date, timedelta

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.constants import BEARD_STYLES, FACE_SHAPES, HAIR_LENGTHS, MAINTENANCE_LEVELS, STYLE_GOALS
from app.utils import format_money


def services_keyboard(services: list[dict], prefix: str = "book_service") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for service in services:
        builder.button(
            text=f"{service['name']} • {format_money(int(service['price']))}",
            callback_data=f"{prefix}:{service['id']}",
        )
    builder.adjust(1)
    return builder.as_markup()


def barbers_keyboard(barbers: list[dict], prefix: str = "book_barber") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for barber in barbers:
        builder.button(
            text=f"{barber['name']} • {barber['specialty']}",
            callback_data=f"{prefix}:{barber['id']}",
        )
    builder.adjust(1)
    return builder.as_markup()


def dates_keyboard(days: int, prefix: str, offset_start: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    today = date.today()
    for offset in range(offset_start, offset_start + days):
        current_day = today + timedelta(days=offset)
        builder.button(
            text=current_day.strftime("%d.%m (%a)"),
            callback_data=f"{prefix}:{current_day.isoformat()}",
        )
    builder.adjust(2)
    return builder.as_markup()


def times_keyboard(times: list[str], prefix: str = "book_time") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in times:
        builder.button(text=item, callback_data=f"{prefix}:{item}")
    builder.adjust(3)
    return builder.as_markup()


def confirm_booking_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Tasdiqlash", callback_data="book_confirm")
    builder.button(text="Bekor qilish", callback_data="book_abort")
    builder.adjust(2)
    return builder.as_markup()


def cancel_booking_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bronni bekor qilish", callback_data=f"user_cancel:{booking_id}")
    return builder.as_markup()


def rating_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for rating in range(1, 6):
        builder.button(text=f"{rating}⭐", callback_data=f"review_rating:{rating}")
    builder.adjust(5)
    return builder.as_markup()


def barber_action_keyboard(barber_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Shu usta bilan bron qilish", callback_data=f"prefill_barber:{barber_id}")
    return builder.as_markup()


def admin_panel_keyboard(pending_barber_applications: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    barber_apps_label = "💼 Barber arizalar"
    if pending_barber_applications > 0:
        barber_apps_label = f"{barber_apps_label} ({pending_barber_applications})"
    buttons = [
        ("📊 Dashboard", "admin:dashboard"),
        ("📅 Bugungi navbatlar", "admin:bookings"),
        ("👥 Mijozlar", "admin:customers"),
        (barber_apps_label, "admin:barber_apps"),
        ("💰 Daromad", "admin:revenue"),
        ("⏰ Jadval", "admin:schedule"),
        ("💈 Xizmatlar", "admin:services"),
        ("⭐ Sharhlar", "admin:reviews"),
        ("⚙️ Sozlamalar", "admin:settings"),
    ]
    for text, data in buttons:
        builder.button(text=text, callback_data=data)
    builder.adjust(2)
    return builder.as_markup()


def back_to_panel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Panelga qaytish", callback_data="admin:panel")
    return builder.as_markup()


def booking_admin_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Completed", callback_data=f"adm_book_done:{booking_id}")
    builder.button(text="❌ Cancel", callback_data=f"adm_book_cancel:{booking_id}")
    builder.button(text="🔄 Reschedule", callback_data=f"adm_book_move:{booking_id}")
    builder.button(text="⬅️ Panel", callback_data="admin:bookings")
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def service_manage_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Xizmat qo'shish", callback_data="adm_srv:add")
    builder.button(text="✏️ Narxni o'zgartirish", callback_data="adm_srv:edit")
    builder.button(text="🗑 Xizmatni o'chirish", callback_data="adm_srv:delete")
    builder.button(text="⬅️ Panel", callback_data="admin:panel")
    builder.adjust(1)
    return builder.as_markup()


def service_picker_keyboard(services: list[dict], prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for service in services:
        builder.button(
            text=f"{service['name']} • {format_money(int(service['price']))}",
            callback_data=f"{prefix}:{service['id']}",
        )
    builder.button(text="⬅️ Xizmatlar", callback_data="admin:services")
    builder.adjust(1)
    return builder.as_markup()


def settings_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🏪 Salon nomi", callback_data="adm_set:shop_name")
    builder.button(text="📍 Manzil", callback_data="adm_set:address")
    builder.button(text="👨‍🦱 Barber nomi", callback_data="adm_set:barber")
    builder.button(text="🕘 Ish vaqti", callback_data="admin:schedule")
    builder.button(text="⬅️ Panel", callback_data="admin:panel")
    builder.adjust(1)
    return builder.as_markup()


def schedule_keyboard(selected_barber_id: int | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if selected_barber_id is not None:
        builder.button(text="👨‍🦱 Ustani almashtirish", callback_data="adm_sch:pick_barber")
    builder.button(text="🕘 Ish vaqti", callback_data="adm_sch:hours")
    builder.button(text="☕ Tanaffus", callback_data="adm_sch:break")
    builder.button(text="📆 Dam olish kunlari", callback_data="adm_sch:offdays")
    builder.button(text="⛔ Blok slot", callback_data="adm_sch:block")
    builder.button(text="⬅️ Panel", callback_data="admin:panel")
    builder.adjust(1)
    return builder.as_markup()


def review_nav_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Panel", callback_data="admin:panel")
    return builder.as_markup()


def choose_barber_for_settings_keyboard(barbers: list[dict], prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for barber in barbers:
        builder.button(text=barber["name"], callback_data=f"{prefix}:{barber['id']}")
    builder.button(text="⬅️ Sozlamalar", callback_data="admin:settings")
    builder.adjust(1)
    return builder.as_markup()


def bookings_list_nav_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Panel", callback_data="admin:panel")
    return builder.as_markup()


def face_shape_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in FACE_SHAPES:
        builder.button(text=item, callback_data=f"rec_face:{item}")
    builder.button(text="Bilmayman", callback_data="rec_face:Bilmayman")
    builder.adjust(2)
    return builder.as_markup()


def hair_length_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in HAIR_LENGTHS:
        builder.button(text=item, callback_data=f"rec_length:{item}")
    builder.adjust(3)
    return builder.as_markup()


def style_goal_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in STYLE_GOALS:
        builder.button(text=item, callback_data=f"rec_style:{item}")
    builder.adjust(1)
    return builder.as_markup()


def maintenance_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in MAINTENANCE_LEVELS:
        builder.button(text=item, callback_data=f"rec_maintenance:{item}")
    builder.adjust(3)
    return builder.as_markup()


def beard_style_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in BEARD_STYLES:
        builder.button(text=item, callback_data=f"rec_beard:{item}")
    builder.adjust(1)
    return builder.as_markup()


def recommendation_card_keyboard(service_id: int | None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if service_id is not None:
        builder.button(text="Shu stil bilan bron qilish", callback_data=f"rec_book:{service_id}")
    builder.adjust(1)
    return builder.as_markup()


def barber_application_admin_keyboard(application_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Tasdiqlash", callback_data=f"adm_barber_approve:{application_id}")
    builder.button(text="Panel", callback_data="admin:panel")
    builder.adjust(1)
    return builder.as_markup()


def local_barber_settings_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Ish vaqti", callback_data="barber_set:hours")
    builder.button(text="Tanaffus", callback_data="barber_set:break")
    builder.button(text="Dam olish kunlari", callback_data="barber_set:offdays")
    builder.button(text="Yo'nalish", callback_data="barber_set:specialty")
    builder.button(text="Telefon", callback_data="barber_set:phone")
    builder.button(text="Bio", callback_data="barber_set:bio")
    builder.adjust(1)
    return builder.as_markup()
