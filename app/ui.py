from __future__ import annotations

from aiogram.types import Message

from app.utils import format_money


async def send_optional_sticker(message: Message, sticker_id: str | None) -> None:
    if not sticker_id:
        return
    try:
        await message.answer_sticker(sticker_id)
    except Exception:
        return


def welcome_text(shop_name: str) -> str:
    return (
        f"<b>{shop_name}</b>\n"
        "━━━━━━━━━━━━━━\n"
        "Premium barber booking assistant\n\n"
        "✂️ Tez bron qilish\n"
        "🤖 AI style tavsiya\n"
        "🎁 Bonus va sodiqlik tizimi\n"
        "📍 Lokatsiya va narxlar\n\n"
        "Pastdagi menyudan kerakli bo'limni tanlang."
    )


def phone_request_text(shop_name: str) -> str:
    return (
        f"<b>{shop_name}</b>\n"
        "━━━━━━━━━━━━━━\n"
        "Mijoz profilingizni qulay boshqarish uchun telefon raqamingizni ulashing.\n\n"
        "Bu ma'lumot:\n"
        "• bron eslatmalari uchun\n"
        "• admin panelda ko'rinish uchun\n"
        "• qayta aloqa uchun kerak bo'ladi"
    )


def price_card(service: dict) -> str:
    return (
        f"<b>💈 {service['name']}</b>\n"
        f"Narx: <b>{format_money(int(service['price']))}</b>\n"
        f"Davomiyligi: {service['duration_minutes']} daqiqa\n"
        f"{service['description']}"
    )


def barber_card(barber: dict) -> str:
    return (
        f"<b>👨‍🦱 {barber['name']}</b>\n"
        f"Yo'nalishi: {barber['specialty']}\n"
        f"Tajriba: {barber['experience_years']} yil"
    )


def booking_preview_text(service: dict, barber: dict, booking_at_text: str) -> str:
    return (
        "<b>✨ Bronni tasdiqlang</b>\n"
        "━━━━━━━━━━━━━━\n"
        f"Xizmat: <b>{service['name']}</b>\n"
        f"Usta: <b>{barber['name']}</b>\n"
        f"Vaqt: <b>{booking_at_text}</b>\n"
        f"Narx: <b>{format_money(int(service['price']))}</b>\n\n"
        "Hammasi to'g'ri bo'lsa, pastdagi tugma orqali tasdiqlang."
    )


def booking_success_text(details: dict, booking_id: int, booking_at_text: str) -> str:
    return (
        "<b>✅ Navbatingiz muvaffaqiyatli bron qilindi</b>\n"
        "━━━━━━━━━━━━━━\n"
        f"Bron ID: <b>#{booking_id}</b>\n"
        f"Xizmat: {details['service_name']}\n"
        f"Usta: {details['barber_name']}\n"
        f"Vaqt: {booking_at_text}\n"
        f"Bonus: +{details['bonus_points_awarded']} ball\n\n"
        "Eslatma xabari navbatdan 30 daqiqa oldin yuboriladi."
    )


def main_menu_hint() -> str:
    return "Asosiy menyu pastda tayyor."


def admin_panel_text() -> str:
    return (
        "<b>Barber AI Admin Panel</b>\n"
        "━━━━━━━━━━━━━━\n"
        "Filial, barber va mijoz oqimini Telegram ichida boshqaring."
    )
