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
        "Premium barber booking assistant'ga xush kelibsiz.\n\n"
        "<b>Mijozlar uchun:</b>\n"
        "• ✂️ Navbat olish: xizmat, usta, sana va vaqt tanlaysiz\n"
        "• 👨‍🦱 Usta tanlash: barberlar profilini ko'rasiz\n"
        "• 🕒 Bo'sh vaqtlar: qaysi slotlar ochiq ekanini ko'rasiz\n"
        "• 🤖 AI style tavsiya: selfie yuborib haircut tavsiya olasiz\n"
        "• 🎁 Bonuslar: ballaringiz va tashriflar soni\n"
        "• ⭐ Sharh qoldirish: xizmat haqida fikr bildirasiz\n\n"
        "<b>Barberlar uchun:</b>\n"
        "• 💼 Sartarosh bo'lish: ariza yuborish\n"
        "• /barber: tasdiqlangandan keyin o'z panelingizga kirish\n"
        "• ⚙️ Sozlamalar: ish vaqti, tanaffus, dam olish kunlari, telefon va bio'ni o'zgartirish\n\n"
        "<b>Kerakli komandalar:</b>\n"
        "• /start\n"
        "• /help\n"
        "• /panel admin uchun\n"
        "• /barber barber panel uchun\n\n"
        "Pastdagi menyudan kerakli bo'limni tanlang."
    )


def help_text() -> str:
    return (
        "<b>Botdan foydalanish yo'riqnomasi</b>\n"
        "━━━━━━━━━━━━━━\n"
        "<b>Mijoz sifatida:</b>\n"
        "1. /start yuboring va ro'yxatdan o'ting\n"
        "2. ✂️ Navbat olish ni bosing\n"
        "3. Xizmat, usta, sana va vaqtni tanlang\n"
        "4. Bronni tasdiqlang\n"
        "5. 30 daqiqa oldin eslatma olasiz\n\n"
        "<b>AI tavsiya:</b>\n"
        "1. 🤖 AI style tavsiya ni bosing\n"
        "2. Selfie yuboring\n"
        "3. Savollarga javob bering\n"
        "4. 3-4 ta haircut tavsiya va bron tugmasini olasiz\n\n"
        "<b>Barber sifatida:</b>\n"
        "1. 💼 Sartarosh bo'lish ni bosing\n"
        "2. Yo'nalish, tajriba, telefon va profil rasmini yuboring\n"
        "3. Admin tasdiqlagach /barber ishlaydi\n"
        "4. ⚙️ Sozlamalar bo'limidan ish vaqti, tanaffus, dam olish kunlari va profilingizni tahrir qilasiz\n\n"
        "<b>Admin sifatida:</b>\n"
        "• /panel orqali dashboard, bronlar, mijozlar va barber arizalarni boshqarasiz"
    )


def barber_panel_intro_text(barber_name: str) -> str:
    return (
        f"<b>{barber_name} uchun barber panel</b>\n"
        "━━━━━━━━━━━━━━\n"
        "Bu panel orqali siz:\n"
        "• bugungi bronlarni ko'rasiz\n"
        "• mijozlar kelishidan oldin signal xabar olasiz\n"
        "• ish vaqtingizni o'zgartirasiz\n"
        "• tanaffus va dam olish kunlarini belgilaysiz\n"
        "• telefon va bio'ni yangilaysiz\n\n"
        "Asosiy bo'limlar pastdagi tugmalarda."
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
        f"Tajriba: {barber['experience_years']} yil\n"
        f"Telefon: {barber.get('phone') or '-'}"
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
