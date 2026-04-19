from __future__ import annotations

from datetime import date, timedelta

from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def barber_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Bronlar"), KeyboardButton(text="👤 Profil")],
            [KeyboardButton(text="✂️ Xizmatlar"), KeyboardButton(text="💰 Narxlar")],
            [KeyboardButton(text="🕒 Ish jadvali"), KeyboardButton(text="⭐ Sharhlar")],
            [KeyboardButton(text="📈 Statistika"), KeyboardButton(text="💬 Chat")],
            [KeyboardButton(text="⚙️ Sozlamalar")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Barber AI panel bo'limini tanlang",
    )


def dashboard_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, data in [
        ("📅 Bronlar", "bp:bookings"),
        ("👤 Profil", "bp:profile"),
        ("✂️ Xizmatlar", "bp:services"),
        ("💰 Narxlar", "bp:pricing"),
        ("🕒 Jadval", "bp:schedule"),
        ("⭐ Sharhlar", "bp:reviews"),
        ("📈 Statistika", "bp:analytics"),
        ("💬 Chat", "bp:chat"),
        ("⚙️ Sozlamalar", "bp:settings"),
    ]:
        builder.button(text=text, callback_data=data)
    builder.adjust(2, 2, 2, 2, 1)
    return builder.as_markup()


def bookings_filter_keyboard(active_key: str = "today") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    items = [
        ("Bugun", "today"),
        ("Kutilayotgan", "upcoming"),
        ("So'rovlar", "pending"),
        ("Yakunlangan", "completed"),
        ("Bekor qilingan", "cancelled"),
    ]
    for label, key in items:
        prefix = "• " if key == active_key else ""
        builder.button(text=f"{prefix}{label}", callback_data=f"bp:bookings:{key}")
    builder.button(text="⬅️ Dashboard", callback_data="bp:dashboard")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def booking_card_keyboard(booking_id: int, status: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if status == "pending":
        builder.button(text="✅ Accept", callback_data=f"bp:booking:accept:{booking_id}")
        builder.button(text="❌ Reject", callback_data=f"bp:booking:reject:{booking_id}")
    if status in {"pending", "accepted"}:
        builder.button(text="✔️ Complete", callback_data=f"bp:booking:complete:{booking_id}")
        builder.button(text="🔄 Reschedule", callback_data=f"bp:booking:reschedule:{booking_id}")
    builder.button(text="⬅️ Bronlar", callback_data="bp:bookings")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def profile_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, data in [
        ("✏️ To'liq ism", "bp:profile:edit:full_name"),
        ("🏢 Salon nomi", "bp:profile:edit:salon_name"),
        ("📞 Telefon", "bp:profile:edit:phone"),
        ("📍 Manzil", "bp:profile:edit:address"),
        ("💼 Tajriba", "bp:profile:edit:experience"),
        ("📝 Bio", "bp:profile:edit:about"),
        ("🖼 Profil rasmi", "bp:profile:photo"),
        ("🎞 Portfolio", "bp:profile:portfolio"),
    ]:
        builder.button(text=text, callback_data=data)
    builder.button(text="⬅️ Dashboard", callback_data="bp:dashboard")
    builder.adjust(2, 2, 2, 2, 1)
    return builder.as_markup()


def services_keyboard(services: list, mode: str = "view") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for service in services:
        suffix = "⏸" if not service.is_active else "✂️"
        builder.button(text=f"{suffix} {service.name}", callback_data=f"bp:service:{mode}:{service.service_id}")
    if mode == "view":
        builder.button(text="➕ Xizmat qo'shish", callback_data="bp:service:add")
    builder.button(text="⬅️ Dashboard", callback_data="bp:dashboard")
    builder.adjust(1)
    return builder.as_markup()


def service_actions_keyboard(service_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, field in [
        ("✏️ Nom", "name"),
        ("📝 Tavsif", "description"),
        ("⏱ Davomiylik", "duration"),
        ("💰 Narx", "price"),
        ("🗑 O'chirish", "delete"),
    ]:
        builder.button(text=text, callback_data=f"bp:service:action:{field}:{service_id}")
    builder.button(text="⬅️ Xizmatlar", callback_data="bp:services")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def pricing_keyboard(services: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for service in services:
        builder.button(text=f"{service.name} • {service.price:,} so'm".replace(",", " "), callback_data=f"bp:pricing:set:{service.service_id}")
    builder.button(text="📦 Bulk update", callback_data="bp:pricing:bulk")
    builder.button(text="⬅️ Dashboard", callback_data="bp:dashboard")
    builder.adjust(1)
    return builder.as_markup()


def schedule_keyboard(schedule_days: list[int], vacation_mode: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    weekdays = ["Du", "Se", "Cho", "Pay", "Ju", "Sha", "Yak"]
    for index, label in enumerate(weekdays):
        prefix = "✅" if index in schedule_days else "▫️"
        builder.button(text=f"{prefix} {label}", callback_data=f"bp:schedule:day:{index}")
    builder.button(text="🕘 Ish vaqti", callback_data="bp:schedule:hours")
    builder.button(text="☕ Break", callback_data="bp:schedule:break")
    builder.button(text="🚫 Sana bloklash", callback_data="bp:schedule:unavailable")
    builder.button(text="🟢 Open slot", callback_data="bp:schedule:custom:open")
    builder.button(text="🔴 Closed slot", callback_data="bp:schedule:custom:closed")
    builder.button(
        text=f"{'🟢' if vacation_mode else '⚪️'} Vacation mode",
        callback_data="bp:schedule:vacation",
    )
    builder.button(text="⬅️ Dashboard", callback_data="bp:dashboard")
    builder.adjust(3, 3, 1, 1, 1, 1, 1)
    return builder.as_markup()


def reviews_keyboard(reviews: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for review in reviews[:5]:
        builder.button(text=f"💬 {review.client_name}", callback_data=f"bp:review:reply:{review.review_id}")
    builder.button(text="⬅️ Dashboard", callback_data="bp:dashboard")
    builder.adjust(1)
    return builder.as_markup()


def chat_threads_keyboard(threads: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for thread in threads:
        badge = f" ({thread.unread_count})" if thread.unread_count else ""
        builder.button(text=f"💬 {thread.client_name}{badge}", callback_data=f"bp:chat:thread:{thread.thread_id}")
    builder.button(text="⬅️ Dashboard", callback_data="bp:dashboard")
    builder.adjust(1)
    return builder.as_markup()


def quick_reply_keyboard(thread_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, key in [
        ("Yo'ldaman", "on_my_way"),
        ("5 daqiqada tayyor", "ready_soon"),
        ("Bron tasdiqlandi", "booking_confirmed"),
        ("Qo'ng'iroq qiling", "call_me"),
    ]:
        builder.button(text=text, callback_data=f"bp:chat:quick:{thread_id}:{key}")
    builder.button(text="✍️ Custom reply", callback_data=f"bp:chat:reply:{thread_id}")
    builder.button(text="⬅️ Inbox", callback_data="bp:chat")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def settings_keyboard(notifications_enabled: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"{'🟢' if notifications_enabled else '⚪️'} Bildirishnomalar",
        callback_data="bp:settings:notifications",
    )
    builder.button(text="🌗 Premium tema", callback_data="bp:settings:theme")
    builder.button(text="⬅️ Dashboard", callback_data="bp:dashboard")
    builder.adjust(1)
    return builder.as_markup()


def reschedule_dates_keyboard(days: int = 10) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    today = date.today()
    for offset in range(days):
        current = today + timedelta(days=offset)
        builder.button(
            text=f"{current.day}-{_month_name(current.month)}",
            callback_data=f"bp:reschedule:date:{current.isoformat()}",
        )
    builder.button(text="⬅️ Bronlar", callback_data="bp:bookings")
    builder.adjust(2, 2, 2, 2, 2, 1)
    return builder.as_markup()


def reschedule_times_keyboard(grouped_slots: dict[str, list[str]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for title, key in [("☀️ 1-qism", "morning"), ("🌙 2-qism", "evening")]:
        slots = grouped_slots.get(key) or []
        if not slots:
            continue
        builder.button(text=title, callback_data="bp:noop")
        for slot in slots:
            builder.button(text=slot, callback_data=f"bp:reschedule:time:{slot}")
    builder.button(text="⬅️ Sana tanlash", callback_data="bp:bookings")
    builder.adjust(1, 3, 1, 3, 1)
    return builder.as_markup()


def _month_name(month: int) -> str:
    mapping = {
        1: "yanvar",
        2: "fevral",
        3: "mart",
        4: "aprel",
        5: "may",
        6: "iyun",
        7: "iyul",
        8: "avgust",
        9: "sentyabr",
        10: "oktyabr",
        11: "noyabr",
        12: "dekabr",
    }
    return mapping[month]

