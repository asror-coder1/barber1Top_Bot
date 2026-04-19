from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Contact, Message

from app.config import Settings
from app.constants import AI_RECOMMENDATION, BECOME_BARBER, BONUSES, CHOOSE_BARBER, FREE_SLOTS, LOCATION, PRICES, REVIEW
from app.database.repository import Repository
from app.keyboards.inline import barber_action_keyboard, barbers_keyboard, rating_keyboard, services_keyboard
from app.keyboards.reply import main_menu_keyboard, registration_phone_keyboard
from app.states.admin import BarberApplicationStates, ContactStates
from app.states.availability import AvailabilityStates
from app.states.booking import BookingStates
from app.states.recommendation import RecommendationStates
from app.states.review import ReviewStates
from app.ui import barber_card, main_menu_hint, price_card, send_optional_sticker, welcome_text
from app.utils import format_money


def get_common_router(repository: Repository, settings: Settings) -> Router:
    router = Router(name="common")

    async def _register_user(
        message: Message,
        *,
        full_name: str | None = None,
        phone: str | None = None,
    ) -> None:
        if not message.from_user:
            return
        await repository.upsert_user(
            telegram_id=message.from_user.id,
            full_name=(full_name or message.from_user.full_name).strip(),
            username=message.from_user.username,
            language_code=message.from_user.language_code,
            phone=phone,
        )

    async def _shop_name() -> str:
        profile = await repository.get_shop_profile(settings.salon_name, settings.salon_address)
        return profile["shop_name"]

    async def _show_registration_name(message: Message) -> None:
        shop_name = await _shop_name()
        await message.answer(
            (
                f"<b>{shop_name}</b>\n"
                "Ro'yxatdan o'tish boshlandi.\n\n"
                "1/2. Ism va familiyangizni yuboring.\n"
                "Misol: Azizbek Karimov"
            )
        )

    async def _show_registration_phone(message: Message, full_name: str) -> None:
        await message.answer(
            (
                f"<b>{full_name}</b>, ro'yxatdan o'tishning oxirgi bosqichi.\n\n"
                "2/2. Telefon raqamingizni yuboring yoki pastdagi tugma orqali ulashing.\n"
                "Misol: +998901234567"
            ),
            reply_markup=registration_phone_keyboard(),
        )

    def _normalize_phone(raw_value: str) -> str | None:
        value = raw_value.strip().replace(" ", "").replace("-", "")
        if value.startswith("998") and not value.startswith("+"):
            value = f"+{value}"
        if value.startswith("8") and len(value) == 9:
            value = f"+998{value}"
        if re.fullmatch(r"\+998\d{9}", value):
            return value
        return None

    @router.message(CommandStart())
    async def start(message: Message, state: FSMContext) -> None:
        await state.clear()
        await send_optional_sticker(message, settings.start_sticker_id)
        if not message.from_user:
            return

        user_profile = await repository.get_user_profile(message.from_user.id)
        if not user_profile:
            await state.set_state(ContactStates.waiting_for_name)
            await _show_registration_name(message)
            return

        if not user_profile.get("phone"):
            await state.set_state(ContactStates.waiting_for_phone)
            await state.update_data(registration_name=user_profile["full_name"])
            await _show_registration_phone(message, user_profile["full_name"])
            return

        shop_name = await _shop_name()
        await message.answer(welcome_text(shop_name), reply_markup=main_menu_keyboard())

    @router.message(ContactStates.waiting_for_name, F.text)
    async def save_name(message: Message, state: FSMContext) -> None:
        full_name = (message.text or "").strip()
        if len(full_name) < 3:
            await message.answer("Ism va familiyani to'liqroq yuboring.")
            return
        await _register_user(message, full_name=full_name)
        await state.set_state(ContactStates.waiting_for_phone)
        await state.update_data(registration_name=full_name)
        await _show_registration_phone(message, full_name)

    @router.message(ContactStates.waiting_for_phone, F.contact)
    async def save_phone_contact(message: Message, state: FSMContext) -> None:
        contact: Contact = message.contact
        if not message.from_user:
            return
        if contact.user_id and contact.user_id != message.from_user.id:
            await message.answer("Iltimos, o'zingizning telefon raqamingizni yuboring.")
            return

        data = await state.get_data()
        await _register_user(
            message,
            full_name=data.get("registration_name"),
            phone=contact.phone_number,
        )
        await state.clear()
        shop_name = await _shop_name()
        await message.answer("✅ Ro'yxatdan o'tish yakunlandi.\n\n" + welcome_text(shop_name), reply_markup=main_menu_keyboard())

    @router.message(ContactStates.waiting_for_phone, F.text)
    async def save_phone_text(message: Message, state: FSMContext) -> None:
        normalized_phone = _normalize_phone(message.text or "")
        if not normalized_phone:
            await message.answer("Telefon raqamini to'g'ri formatda yuboring. Misol: +998901234567")
            return

        data = await state.get_data()
        await _register_user(
            message,
            full_name=data.get("registration_name"),
            phone=normalized_phone,
        )
        await state.clear()
        shop_name = await _shop_name()
        await message.answer("✅ Ro'yxatdan o'tish yakunlandi.\n\n" + welcome_text(shop_name), reply_markup=main_menu_keyboard())

    @router.message(F.text == CHOOSE_BARBER)
    async def choose_barber(message: Message) -> None:
        await _register_user(message)
        barbers = await repository.list_barbers()
        for barber in barbers:
            if barber.get("photo_file_id"):
                await message.answer_photo(
                    photo=barber["photo_file_id"],
                    caption=barber_card(barber),
                    reply_markup=barber_action_keyboard(barber["id"]),
                )
            else:
                await message.answer(barber_card(barber), reply_markup=barber_action_keyboard(barber["id"]))

    @router.callback_query(F.data.startswith("prefill_barber:"))
    async def prefill_barber(callback: CallbackQuery, state: FSMContext) -> None:
        barber_id = int(callback.data.split(":", maxsplit=1)[1])
        await state.set_state(BookingStates.service)
        await state.update_data(prefill_barber_id=barber_id)
        services = await repository.list_services()
        await callback.message.answer(
            "✨ Xizmat turini tanlang:",
            reply_markup=services_keyboard(services, prefix="prefill_service"),
        )
        await callback.answer()

    @router.message(F.text == PRICES)
    async def show_prices(message: Message) -> None:
        await _register_user(message)
        services = await repository.list_services()
        lines = ["<b>💰 Xizmatlar va narxlar</b>", "━━━━━━━━━━━━━━"]
        for service in services:
            lines.append(price_card(service))
        await message.answer("\n".join(lines), reply_markup=main_menu_keyboard())

    @router.message(F.text == BONUSES)
    async def show_bonuses(message: Message) -> None:
        await _register_user(message)
        if not message.from_user:
            return
        summary = await repository.get_bonus_summary(message.from_user.id)
        if not summary:
            await message.answer("Bonus ma'lumotlari topilmadi.", reply_markup=main_menu_keyboard())
            return
        text = (
            "<b>🎁 Bonus dasturi</b>\n"
            "━━━━━━━━━━━━━━\n"
            f"Joriy bonuslaringiz: <b>{summary['loyalty_points']} ball</b>\n"
            f"Bronlar soni: {summary['total_bookings']}\n"
            f"Umumiy xarajat: {format_money(int(summary['total_spent']))}\n\n"
            "Har bir tasdiqlangan bron uchun taxminan 5% ekvivalent bonus ball qo'shiladi."
        )
        await message.answer(text, reply_markup=main_menu_keyboard())

    @router.message(F.text == LOCATION)
    async def show_location(message: Message) -> None:
        await _register_user(message)
        profile = await repository.get_shop_profile(settings.salon_name, settings.salon_address)
        await message.answer_location(settings.salon_latitude, settings.salon_longitude)
        await message.answer(
            f"<b>📍 {profile['shop_name']}</b>\n━━━━━━━━━━━━━━\n{profile['address']}",
            reply_markup=main_menu_keyboard(),
        )

    @router.message(F.text == FREE_SLOTS)
    async def start_availability(message: Message, state: FSMContext) -> None:
        await _register_user(message)
        await state.set_state(AvailabilityStates.barber)
        barbers = await repository.list_barbers()
        await message.answer(
            "🕒 Bo'sh vaqtlarni ko'rish uchun ustani tanlang:",
            reply_markup=barbers_keyboard(barbers, prefix="availability_barber"),
        )

    @router.message(F.text == REVIEW)
    async def start_review(message: Message, state: FSMContext) -> None:
        await _register_user(message)
        await state.set_state(ReviewStates.rating)
        await message.answer("⭐ Xizmatni 1 dan 5 gacha baholang:", reply_markup=rating_keyboard())

    @router.message(F.text == AI_RECOMMENDATION)
    async def start_recommendation(message: Message, state: FSMContext) -> None:
        await _register_user(message)
        await state.set_state(RecommendationStates.photo)
        await message.answer(
            "🤖 AI style tavsiya uchun avval yuzingiz aniq ko'rinadigan selfie yuboring.\n\n"
            "Tavsiya: kamera to'g'ridan-to'g'ri yuzga qaragan, yorug'lik yaxshi va bosh qismi to'liq ko'rinsin.",
            reply_markup=main_menu_keyboard(),
        )

    @router.message(F.text == BECOME_BARBER)
    async def start_barber_application(message: Message, state: FSMContext) -> None:
        await _register_user(message)
        if not message.from_user:
            return
        existing_barber = await repository.get_barber_by_telegram_id(message.from_user.id)
        if existing_barber:
            await message.answer(
                "Siz allaqachon barber sifatida tasdiqlangansiz. Panelga kirish uchun /barber ni yuboring.",
                reply_markup=main_menu_keyboard(),
            )
            return
        profile = await repository.get_user_profile(message.from_user.id)
        await state.set_state(BarberApplicationStates.specialty)
        await state.update_data(
            barber_application_name=(profile or {}).get("full_name", message.from_user.full_name),
            barber_application_phone=(profile or {}).get("phone", ""),
        )
        await message.answer(
            "Sartarosh arizasi boshlandi.\n\n1/3. Yo'nalishingizni yozing.\nMasalan: fade, classic cuts, beard styling"
        )

    @router.message(BarberApplicationStates.specialty, F.text)
    async def barber_application_specialty(message: Message, state: FSMContext) -> None:
        specialty = (message.text or "").strip()
        if len(specialty) < 4:
            await message.answer("Yo'nalishni biroz to'liqroq yozing.")
            return
        await state.update_data(barber_application_specialty=specialty)
        await state.set_state(BarberApplicationStates.experience)
        await message.answer("2/3. Tajribangizni yil ko'rinishida yuboring. Masalan: 4")

    @router.message(BarberApplicationStates.experience, F.text)
    async def barber_application_experience(message: Message, state: FSMContext) -> None:
        experience_text = (message.text or "").strip()
        if not experience_text.isdigit():
            await message.answer("Tajriba yilini raqam bilan yuboring. Masalan: 4")
            return
        await state.update_data(barber_application_experience=int(experience_text))
        await state.set_state(BarberApplicationStates.phone)
        data = await state.get_data()
        current_phone = data.get("barber_application_phone") or ""
        suffix = f"\nHozirgi telefon: {current_phone}" if current_phone else ""
        await message.answer(
            "3/3. Ishchi telefon raqamingizni yuboring. Masalan: +998901234567" + suffix
        )

    @router.message(BarberApplicationStates.phone, F.text)
    async def barber_application_phone(message: Message, state: FSMContext) -> None:
        normalized_phone = _normalize_phone(message.text or "")
        if not normalized_phone:
            await message.answer("Telefon raqamini to'g'ri formatda yuboring. Misol: +998901234567")
            return
        await state.update_data(barber_application_phone=normalized_phone)
        await state.set_state(BarberApplicationStates.photo)
        await message.answer("4/4. Endi o'zingizning profil rasmingizni yuboring.")

    @router.message(BarberApplicationStates.photo, F.photo)
    async def barber_application_photo(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        if not message.from_user:
            return
        photo_file_id = message.photo[-1].file_id
        await repository.create_barber_application(
            telegram_id=message.from_user.id,
            full_name=data["barber_application_name"],
            username=message.from_user.username,
            phone=data["barber_application_phone"],
            specialty=data["barber_application_specialty"],
            experience_years=int(data["barber_application_experience"]),
            photo_file_id=photo_file_id,
        )
        await state.clear()
        await message.answer(
            "Arizangiz admin ko'rib chiqishi uchun yuborildi. Tasdiqlangandan keyin /barber orqali o'z panelingizga kira olasiz.",
            reply_markup=main_menu_keyboard(),
        )

    @router.message(BarberApplicationStates.photo)
    async def barber_application_photo_invalid(message: Message) -> None:
        await message.answer("Iltimos, barber profilingiz uchun rasm yuboring.")

    @router.message()
    async def fallback(message: Message) -> None:
        await _register_user(message)
        await message.answer("Menudagi bo'limlardan birini tanlang.", reply_markup=main_menu_keyboard())

    return router
