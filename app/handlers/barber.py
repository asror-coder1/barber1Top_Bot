from __future__ import annotations

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.database.repository import Repository
from app.keyboards.inline import local_barber_settings_keyboard
from app.keyboards.reply import barber_panel_keyboard, main_menu_keyboard
from app.states.barber_local import LocalBarberSettingsStates
from app.utils import format_datetime_uz, format_money, now_local, parse_time_range


def get_local_barber_router(repository: Repository, settings) -> Router:
    router = Router(name="local_barber")

    async def _resolve_barber(message: Message) -> dict | None:
        if not message.from_user:
            return None
        return await repository.get_barber_by_telegram_id(message.from_user.id)

    async def _require_barber(message: Message) -> dict | None:
        barber = await _resolve_barber(message)
        if barber is None:
            await message.answer(
                "Sizning akkauntingiz hech qaysi barber profiliga biriktirilmagan. "
                "Har bir barber faqat o'z telegram akkaunti bilan o'z paneliga kiradi.\n\n"
                "Agar siz barber bo'lsangiz `💼 Sartarosh bo'lish` orqali ariza yuboring yoki admin shu akkauntni tasdiqlasin.",
                reply_markup=main_menu_keyboard(),
            )
            return None
        return barber

    async def _show_dashboard(message: Message, barber: dict) -> None:
        today = now_local(repository.timezone).date()
        stats = await repository.get_barber_dashboard_stats(barber["id"], today)
        await message.answer(
            (
                f"<b>{barber['name']} uchun barber panel</b>\n\n"
                f"Bugungi bronlar: <b>{stats['total_bookings']}</b>\n"
                f"Bugungi tushum: <b>{format_money(stats['revenue'])}</b>\n"
                f"Bekor qilingan: <b>{stats['cancelled_count']}</b>\n"
                f"Yo'nalish: <b>{barber['specialty']}</b>"
            ),
            reply_markup=barber_panel_keyboard(),
        )

    async def _show_bookings(message: Message, barber: dict, *, upcoming_only: bool) -> None:
        bookings = await repository.list_barber_bookings(barber["id"], upcoming_only=upcoming_only)
        title = "Kelgusi bronlar" if upcoming_only else "Bugungi bronlar"
        if not bookings:
            await message.answer(f"{title} hozircha yo'q.", reply_markup=barber_panel_keyboard())
            return
        await message.answer(f"<b>{title}</b>", reply_markup=barber_panel_keyboard())
        for item in bookings:
            booking_at = datetime.fromisoformat(item["booking_at"])
            await message.answer(
                (
                    f"<b>#{item['id']} • {item['full_name']}</b>\n"
                    f"Telefon: {item['phone']}\n"
                    f"Xizmat: {item['service_name']}\n"
                    f"Vaqt: {format_datetime_uz(booking_at)}\n"
                    f"Status: {item['status']}"
                )
            )

    async def _show_schedule(message: Message, barber: dict) -> None:
        schedule_data = await repository.get_schedule(barber["id"])
        off_days_text = schedule_data["off_days"] or "yo'q"
        await message.answer(
            (
                f"<b>{barber['name']} jadvali</b>\n\n"
                f"Ish vaqti: {schedule_data['work_start']} - {schedule_data['work_end']}\n"
                f"Tanaffus: {schedule_data['break_start'] or '-'} - {schedule_data['break_end'] or '-'}\n"
                f"Dam olish kunlari: {off_days_text}"
            ),
            reply_markup=barber_panel_keyboard(),
        )

    async def _show_profile(message: Message, barber: dict) -> None:
        text = (
            f"<b>{barber['name']}</b>\n"
            f"Yo'nalish: {barber['specialty']}\n"
            f"Tajriba: {barber['experience_years']} yil\n"
            f"Telefon: {barber['phone'] or '-'}\n"
            f"Bio: {barber['bio'] or '-'}"
        )
        if barber.get("photo_file_id"):
            await message.answer_photo(
                photo=barber["photo_file_id"],
                caption=text,
                reply_markup=barber_panel_keyboard(),
            )
        else:
            await message.answer(text, reply_markup=barber_panel_keyboard())

    async def _show_settings(message: Message, barber: dict) -> None:
        schedule_data = await repository.get_schedule(barber["id"])
        off_days_text = schedule_data["off_days"] or "yo'q"
        await message.answer(
            (
                "<b>⚙️ Sozlamalar</b>\n\n"
                f"Ish vaqti: {schedule_data['work_start']} - {schedule_data['work_end']}\n"
                f"Tanaffus: {schedule_data['break_start'] or '-'} - {schedule_data['break_end'] or '-'}\n"
                f"Dam olish kunlari: {off_days_text}\n"
                f"Yo'nalish: {barber['specialty']}\n"
                f"Telefon: {barber['phone'] or '-'}\n"
                f"Bio: {barber['bio'] or '-'}\n\n"
                "Pastdagi bo'limdan tahrir qilmoqchi bo'lgan narsani tanlang."
            ),
            reply_markup=local_barber_settings_keyboard(),
        )

    @router.message(Command("barber"))
    async def barber_entry(message: Message) -> None:
        barber = await _require_barber(message)
        if barber is not None:
            await _show_dashboard(message, barber)

    @router.message(F.text == "📈 Dashboard")
    async def dashboard(message: Message) -> None:
        barber = await _require_barber(message)
        if barber is not None:
            await _show_dashboard(message, barber)

    @router.message(F.text == "📅 Mening bronlarim")
    async def bookings(message: Message) -> None:
        barber = await _require_barber(message)
        if barber is not None:
            await _show_bookings(message, barber, upcoming_only=False)

    @router.message(F.text == "🕒 Mening jadvalim")
    async def schedule(message: Message) -> None:
        barber = await _require_barber(message)
        if barber is not None:
            await _show_schedule(message, barber)

    @router.message(F.text == "👤 Mening profilim")
    async def profile(message: Message) -> None:
        barber = await _require_barber(message)
        if barber is not None:
            await _show_profile(message, barber)

    @router.message(F.text == "⚙️ Sozlamalar")
    async def settings_menu(message: Message) -> None:
        barber = await _require_barber(message)
        if barber is not None:
            await _show_settings(message, barber)

    @router.callback_query(F.data == "barber_set:hours")
    async def settings_hours(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(LocalBarberSettingsStates.working_hours)
        await callback.message.answer("Yangi ish vaqtini yuboring. Format: 09:00-21:00")
        await callback.answer()

    @router.callback_query(F.data == "barber_set:break")
    async def settings_break(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(LocalBarberSettingsStates.break_time)
        await callback.message.answer("Yangi tanaffus vaqtini yuboring. Format: 13:00-14:00 yoki yo'q")
        await callback.answer()

    @router.callback_query(F.data == "barber_set:offdays")
    async def settings_offdays(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(LocalBarberSettingsStates.off_days)
        await callback.message.answer("Dam olish kunlarini yuboring. Misol: 0,6 yoki bo'sh")
        await callback.answer()

    @router.callback_query(F.data == "barber_set:specialty")
    async def settings_specialty(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(LocalBarberSettingsStates.specialty)
        await callback.message.answer("Yangi yo'nalishingizni yuboring.")
        await callback.answer()

    @router.callback_query(F.data == "barber_set:phone")
    async def settings_phone(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(LocalBarberSettingsStates.phone)
        await callback.message.answer("Yangi telefon raqamingizni yuboring. Misol: +998901234567")
        await callback.answer()

    @router.callback_query(F.data == "barber_set:bio")
    async def settings_bio(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(LocalBarberSettingsStates.bio)
        await callback.message.answer("Qisqa bio yuboring.")
        await callback.answer()

    @router.message(LocalBarberSettingsStates.working_hours)
    async def save_hours(message: Message, state: FSMContext) -> None:
        barber = await _require_barber(message)
        if barber is None:
            return
        try:
            start_time, end_time = parse_time_range(message.text or "")
        except Exception:
            await message.answer("Format xato. Masalan: 09:00-21:00")
            return
        await repository.update_schedule_hours(barber["id"], start_time, end_time)
        await state.clear()
        await _show_settings(message, await repository.get_barber(barber["id"]))

    @router.message(LocalBarberSettingsStates.break_time)
    async def save_break(message: Message, state: FSMContext) -> None:
        barber = await _require_barber(message)
        if barber is None:
            return
        raw = (message.text or "").strip().lower()
        if raw in {"yo'q", "yoq", "none", "-"}:
            break_start = break_end = None
        else:
            try:
                break_start, break_end = parse_time_range(message.text or "")
            except Exception:
                await message.answer("Format xato. Masalan: 13:00-14:00 yoki yo'q")
                return
        await repository.update_schedule_break(barber["id"], break_start, break_end)
        await state.clear()
        await _show_settings(message, await repository.get_barber(barber["id"]))

    @router.message(LocalBarberSettingsStates.off_days)
    async def save_offdays(message: Message, state: FSMContext) -> None:
        barber = await _require_barber(message)
        if barber is None:
            return
        raw = (message.text or "").replace(" ", "")
        if raw:
            valid = all(item.isdigit() and 0 <= int(item) <= 6 for item in raw.split(",") if item)
            if not valid:
                await message.answer("Faqat 0 dan 6 gacha raqamlar kiriting. Misol: 0,6")
                return
        await repository.update_schedule_off_days(barber["id"], raw)
        await state.clear()
        await _show_settings(message, await repository.get_barber(barber["id"]))

    @router.message(LocalBarberSettingsStates.specialty)
    async def save_specialty(message: Message, state: FSMContext) -> None:
        barber = await _require_barber(message)
        if barber is None:
            return
        specialty = (message.text or "").strip()
        if len(specialty) < 4:
            await message.answer("Yo'nalishni biroz to'liqroq yozing.")
            return
        await repository.update_barber_profile(
            barber["id"],
            specialty=specialty,
            phone=barber.get("phone"),
            bio=barber.get("bio"),
        )
        await state.clear()
        await _show_settings(message, await repository.get_barber(barber["id"]))

    @router.message(LocalBarberSettingsStates.phone)
    async def save_phone(message: Message, state: FSMContext) -> None:
        barber = await _require_barber(message)
        if barber is None:
            return
        phone = (message.text or "").strip()
        if not phone:
            await message.answer("Telefon raqamini yuboring.")
            return
        await repository.update_barber_profile(
            barber["id"],
            specialty=barber["specialty"],
            phone=phone,
            bio=barber.get("bio"),
        )
        await state.clear()
        await _show_settings(message, await repository.get_barber(barber["id"]))

    @router.message(LocalBarberSettingsStates.bio)
    async def save_bio(message: Message, state: FSMContext) -> None:
        barber = await _require_barber(message)
        if barber is None:
            return
        bio = (message.text or "").strip()
        await repository.update_barber_profile(
            barber["id"],
            specialty=barber["specialty"],
            phone=barber.get("phone"),
            bio=bio,
        )
        await state.clear()
        await _show_settings(message, await repository.get_barber(barber["id"]))

    return router
