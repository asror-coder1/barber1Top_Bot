from __future__ import annotations

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import Settings
from app.database.repository import Repository
from app.keyboards.inline import (
    admin_panel_keyboard,
    back_to_panel_keyboard,
    barber_application_admin_keyboard,
    barbers_keyboard,
    booking_admin_keyboard,
    bookings_list_nav_keyboard,
    choose_barber_for_settings_keyboard,
    dates_keyboard,
    review_nav_keyboard,
    schedule_keyboard,
    settings_keyboard,
    service_manage_keyboard,
    service_picker_keyboard,
    times_keyboard,
)
from app.states.admin import RescheduleStates, ScheduleStates, ServiceStates, SettingsStates
from app.ui import admin_panel_text, send_optional_sticker
from app.utils import (
    format_money,
    format_status_uz,
    now_local,
    parse_time_range,
    weekday_name_uz,
)


def get_admin_router(repository: Repository, settings: Settings) -> Router:
    router = Router(name="admin")

    def _message_is_admin(message: Message) -> bool:
        if not settings.admin_ids:
            return True
        return bool(message.from_user and message.from_user.id in settings.admin_ids)

    def _callback_is_admin(callback: CallbackQuery) -> bool:
        if not settings.admin_ids:
            return True
        return bool(callback.from_user and callback.from_user.id in settings.admin_ids)

    async def _deny_message(message: Message) -> None:
        await message.answer("Bu panel faqat admin, filial menejeri yoki barber staff uchun.")

    async def _deny_callback(callback: CallbackQuery) -> None:
        await callback.answer("Ruxsat yo'q", show_alert=True)

    async def _selected_barber_id(state: FSMContext) -> int | None:
        data = await state.get_data()
        if data.get("admin_barber_id"):
            return int(data["admin_barber_id"])
        barbers = await repository.list_barbers()
        return int(barbers[0]["id"]) if barbers else None

    async def _render_dashboard_text() -> str:
        today = now_local(repository.timezone).date()
        stats = await repository.get_dashboard_stats(today)
        return (
            "<b>📊 Dashboard</b>\n\n"
            f"Bugun: {stats['today_bookings']} ta navbat\n"
            f"Daromad: {format_money(stats['today_revenue'])}\n"
            f"Haftalik daromad: {format_money(stats['weekly_revenue'])}\n"
            f"Yangi mijozlar: {stats['new_customers']}\n"
            f"Bekor qilingan: {stats['cancelled_bookings']}"
        )

    async def _render_revenue_text() -> str:
        stats = await repository.get_revenue_stats(now_local(repository.timezone).date())
        return (
            "<b>💰 Daromad</b>\n\n"
            f"Kunlik: {format_money(stats['daily'])}\n"
            f"Haftalik: {format_money(stats['weekly'])}\n"
            f"Oylik: {format_money(stats['monthly'])}"
        )

    async def _render_customers_text() -> str:
        customers = await repository.list_customers()
        if not customers:
            return "<b>👥 Mijozlar</b>\n\nHozircha mijozlar yo'q."
        lines = ["<b>👥 Mijozlar</b>"]
        for item in customers:
            last_visit = "-"
            if item["last_visit_date"]:
                last_visit = datetime.fromisoformat(item["last_visit_date"]).strftime("%d.%m.%Y")
            lines.append(
                "\n"
                f"<b>{item['full_name']}</b>\n"
                f"Telefon: {item['phone']}\n"
                f"Tashriflar: {item['visit_count']}\n"
                f"So'nggi haircut: {item['last_haircut'] or '-'}\n"
                f"So'nggi tashrif: {last_visit}"
            )
        return "\n".join(lines)

    async def _render_barber_applications_text() -> str:
        applications = await repository.list_pending_barber_applications()
        if not applications:
            return "<b>💼 Barber arizalar</b>\n\nHozircha kutilayotgan ariza yo'q."
        lines = ["<b>💼 Barber arizalar</b>"]
        for item in applications:
            created = datetime.fromisoformat(item["created_at"]).strftime("%d.%m %H:%M")
            username = f"@{item['username']}" if item["username"] else "-"
            lines.append(
                "\n"
                f"<b>#{item['id']} • {item['full_name']}</b>\n"
                f"Telegram ID: {item['telegram_id']}\n"
                f"Username: {username}\n"
                f"Telefon: {item['phone']}\n"
                f"Yo'nalish: {item['specialty']}\n"
                f"Tajriba: {item['experience_years']} yil\n"
                f"Yuborilgan: {created}"
            )
        return "\n".join(lines)

    async def _render_services_text() -> str:
        services = await repository.list_services(include_inactive=True)
        lines = ["<b>💈 Xizmatlar</b>"]
        for service in services:
            status = "Aktiv" if service["is_active"] else "O'chirilgan"
            lines.append(
                f"\n<b>{service['name']}</b>\n"
                f"Narx: {format_money(int(service['price']))}\n"
                f"Davomiyligi: {service['duration_minutes']} daqiqa\n"
                f"Holat: {status}"
            )
        return "\n".join(lines)

    async def _render_reviews_text() -> str:
        summary = await repository.get_reviews_summary()
        reviews = await repository.list_reviews()
        lines = [
            "<b>⭐ Sharhlar</b>",
            f"O'rtacha reyting: {summary['avg_rating']:.1f}",
            f"Jami sharhlar: {summary['total_reviews']}",
        ]
        for item in reviews:
            created = datetime.fromisoformat(item["created_at"]).strftime("%d.%m %H:%M")
            lines.append(
                f"\n<b>{item['full_name']}</b> • {item['rating']}⭐ • {created}\n"
                f"{item['comment'] or 'Izoh qoldirilmagan'}"
            )
        return "\n".join(lines)

    async def _render_settings_text() -> str:
        profile = await repository.get_shop_profile(settings.salon_name, settings.salon_address)
        barbers = await repository.list_barbers()
        barber_names = ", ".join(item["name"] for item in barbers) if barbers else "-"
        return (
            "<b>⚙️ Sozlamalar</b>\n\n"
            f"Salon nomi: {profile['shop_name']}\n"
            f"Manzil: {profile['address']}\n"
            f"Barberlar: {barber_names}\n"
            "Ish vaqtini o'zgartirish uchun Jadval sahifasidan foydalaning."
        )

    async def _render_schedule_text(state: FSMContext) -> str:
        barber_id = await _selected_barber_id(state)
        if barber_id is None:
            return "<b>⏰ Jadval</b>\n\nBarber topilmadi."
        barber = await repository.get_barber(barber_id)
        schedule = await repository.get_schedule(barber_id)
        off_days = schedule["off_days"] or ""
        off_days_text = (
            ", ".join(weekday_name_uz(int(item.strip())) for item in off_days.split(",") if item.strip().isdigit())
            or "Yo'q"
        )
        break_text = (
            f"{schedule['break_start']} - {schedule['break_end']}"
            if schedule["break_start"] and schedule["break_end"]
            else "Yo'q"
        )
        today_blocks = ", ".join(await repository.list_blocked_slots(barber_id, now_local(repository.timezone).date())) or "Yo'q"
        return (
            "<b>⏰ Jadval</b>\n\n"
            f"Usta: {barber['name']}\n"
            f"Ish vaqti: {schedule['work_start']} - {schedule['work_end']}\n"
            f"Tanaffus: {break_text}\n"
            f"Dam olish kunlari: {off_days_text}\n"
            f"Bugungi blok slotlar: {today_blocks}"
        )

    async def _booking_card_text(booking: dict) -> str:
        booking_at = datetime.fromisoformat(booking["booking_at"])
        return (
            f"<b>#{booking['id']} • {booking['full_name']}</b>\n"
            f"Telefon: {booking['phone']}\n"
            f"Xizmat: {booking['service_name']}\n"
            f"Usta: {booking['barber_name']}\n"
            f"Vaqt: {booking_at.strftime('%H:%M')}\n"
            f"Status: {format_status_uz(booking['status'])}"
        )

    async def _send_bookings_cards(message: Message) -> None:
        bookings = await repository.list_today_bookings(now_local(repository.timezone).date())
        if not bookings:
            await message.answer("Bugun uchun navbatlar yo'q.", reply_markup=bookings_list_nav_keyboard())
            return
        for item in bookings:
            await message.answer(await _booking_card_text(item), reply_markup=booking_admin_keyboard(item["id"]))

    @router.message(Command("panel"))
    async def panel(message: Message) -> None:
        if not _message_is_admin(message):
            await _deny_message(message)
            return
        await send_optional_sticker(message, settings.admin_sticker_id)
        await message.answer(admin_panel_text(), reply_markup=admin_panel_keyboard())

    @router.message(Command("bookings"))
    async def bookings(message: Message) -> None:
        if not _message_is_admin(message):
            await _deny_message(message)
            return
        await message.answer("<b>📅 Bugungi navbatlar</b>", reply_markup=bookings_list_nav_keyboard())
        await _send_bookings_cards(message)

    @router.message(Command("customers"))
    async def customers(message: Message) -> None:
        if not _message_is_admin(message):
            await _deny_message(message)
            return
        await message.answer(await _render_customers_text(), reply_markup=back_to_panel_keyboard())

    @router.message(Command("barber_requests"))
    async def barber_requests(message: Message) -> None:
        if not _message_is_admin(message):
            await _deny_message(message)
            return
        await message.answer(await _render_barber_applications_text(), reply_markup=back_to_panel_keyboard())
        applications = await repository.list_pending_barber_applications()
        for item in applications:
            await message.answer(
                f"Ariza #{item['id']} ni ko'rib chiqing.",
                reply_markup=barber_application_admin_keyboard(item["id"]),
            )

    @router.message(Command("revenue"))
    async def revenue(message: Message) -> None:
        if not _message_is_admin(message):
            await _deny_message(message)
            return
        await message.answer(await _render_revenue_text(), reply_markup=back_to_panel_keyboard())

    @router.message(Command("schedule"))
    async def schedule(message: Message, state: FSMContext) -> None:
        if not _message_is_admin(message):
            await _deny_message(message)
            return
        barber_id = await _selected_barber_id(state)
        await message.answer(await _render_schedule_text(state), reply_markup=schedule_keyboard(barber_id))

    @router.message(Command("services"))
    async def services(message: Message) -> None:
        if not _message_is_admin(message):
            await _deny_message(message)
            return
        await message.answer(await _render_services_text(), reply_markup=service_manage_keyboard())

    @router.message(Command("reviews"))
    async def reviews(message: Message) -> None:
        if not _message_is_admin(message):
            await _deny_message(message)
            return
        await message.answer(await _render_reviews_text(), reply_markup=review_nav_keyboard())

    @router.message(Command("settings"))
    async def settings_page(message: Message) -> None:
        if not _message_is_admin(message):
            await _deny_message(message)
            return
        await message.answer(await _render_settings_text(), reply_markup=settings_keyboard())

    @router.callback_query(F.data == "admin:panel")
    async def cb_panel(callback: CallbackQuery, state: FSMContext) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        await state.clear()
        await callback.message.edit_text(admin_panel_text(), reply_markup=admin_panel_keyboard())
        await callback.answer()

    @router.callback_query(F.data == "admin:dashboard")
    async def cb_dashboard(callback: CallbackQuery) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        await callback.message.edit_text(await _render_dashboard_text(), reply_markup=admin_panel_keyboard())
        await callback.answer()

    @router.callback_query(F.data == "admin:bookings")
    async def cb_bookings(callback: CallbackQuery) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        await callback.message.edit_text("<b>📅 Bugungi navbatlar</b>", reply_markup=bookings_list_nav_keyboard())
        await _send_bookings_cards(callback.message)
        await callback.answer()

    @router.callback_query(F.data == "admin:customers")
    async def cb_customers(callback: CallbackQuery) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        await callback.message.edit_text(await _render_customers_text(), reply_markup=back_to_panel_keyboard())
        await callback.answer()

    @router.callback_query(F.data == "admin:barber_apps")
    async def cb_barber_apps(callback: CallbackQuery) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        await callback.message.edit_text(await _render_barber_applications_text(), reply_markup=back_to_panel_keyboard())
        applications = await repository.list_pending_barber_applications()
        for item in applications:
            await callback.message.answer(
                f"Ariza #{item['id']} ni ko'rib chiqing.",
                reply_markup=barber_application_admin_keyboard(item["id"]),
            )
        await callback.answer()

    @router.callback_query(F.data.startswith("adm_barber_approve:"))
    async def approve_barber_application(callback: CallbackQuery) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        application_id = int(callback.data.split(":", maxsplit=1)[1])
        barber = await repository.approve_barber_application(application_id)
        if not barber:
            await callback.answer("Ariza topilmadi yoki allaqachon ko'rib chiqilgan.", show_alert=True)
            return
        await callback.message.edit_text(
            f"Ariza tasdiqlandi.\n\nBarber: <b>{barber['name']}</b>\nYo'nalish: {barber['specialty']}"
        )
        await callback.answer("Barber tasdiqlandi")

    @router.callback_query(F.data == "admin:revenue")
    async def cb_revenue(callback: CallbackQuery) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        await callback.message.edit_text(await _render_revenue_text(), reply_markup=back_to_panel_keyboard())
        await callback.answer()

    @router.callback_query(F.data == "admin:schedule")
    async def cb_schedule(callback: CallbackQuery, state: FSMContext) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        barber_id = await _selected_barber_id(state)
        await callback.message.edit_text(
            await _render_schedule_text(state),
            reply_markup=schedule_keyboard(barber_id),
        )
        await callback.answer()

    @router.callback_query(F.data == "admin:services")
    async def cb_services(callback: CallbackQuery, state: FSMContext) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        await state.clear()
        await callback.message.edit_text(await _render_services_text(), reply_markup=service_manage_keyboard())
        await callback.answer()

    @router.callback_query(F.data == "admin:reviews")
    async def cb_reviews(callback: CallbackQuery) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        await callback.message.edit_text(await _render_reviews_text(), reply_markup=review_nav_keyboard())
        await callback.answer()

    @router.callback_query(F.data == "admin:settings")
    async def cb_settings(callback: CallbackQuery, state: FSMContext) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        await state.clear()
        await callback.message.edit_text(await _render_settings_text(), reply_markup=settings_keyboard())
        await callback.answer()

    @router.callback_query(F.data.startswith("adm_book_done:"))
    async def booking_done(callback: CallbackQuery) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        booking_id = int(callback.data.split(":", maxsplit=1)[1])
        success = await repository.complete_booking(booking_id)
        if not success:
            await callback.answer("Bronni yakunlab bo'lmadi.", show_alert=True)
            return
        booking = await repository.get_admin_booking(booking_id)
        await callback.message.edit_text(await _booking_card_text(booking), reply_markup=booking_admin_keyboard(booking_id))
        await callback.answer("Status: Completed")

    @router.callback_query(F.data.startswith("adm_book_cancel:"))
    async def booking_cancel(callback: CallbackQuery) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        booking_id = int(callback.data.split(":", maxsplit=1)[1])
        success = await repository.admin_cancel_booking(booking_id)
        if not success:
            await callback.answer("Bronni bekor qilib bo'lmadi.", show_alert=True)
            return
        booking = await repository.get_admin_booking(booking_id)
        await callback.message.edit_text(await _booking_card_text(booking), reply_markup=booking_admin_keyboard(booking_id))
        await callback.answer("Bron bekor qilindi")

    @router.callback_query(F.data.startswith("adm_book_move:"))
    async def booking_reschedule(callback: CallbackQuery, state: FSMContext) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        booking_id = int(callback.data.split(":", maxsplit=1)[1])
        booking = await repository.get_admin_booking(booking_id)
        if not booking:
            await callback.answer("Bron topilmadi.", show_alert=True)
            return
        await state.set_state(RescheduleStates.date)
        await state.update_data(
            reschedule_booking_id=booking_id,
            admin_barber_id=booking["barber_id"],
            reschedule_duration=booking["duration_minutes"],
        )
        await callback.message.edit_text(
            f"#{booking_id} uchun yangi sanani tanlang:",
            reply_markup=dates_keyboard(7, prefix="adm_move_date"),
        )
        await callback.answer()

    @router.callback_query(RescheduleStates.date, F.data.startswith("adm_move_date:"))
    async def reschedule_date(callback: CallbackQuery, state: FSMContext) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        data = await state.get_data()
        booking_date = callback.data.split(":", maxsplit=1)[1]
        slots = await repository.list_available_slots(
            barber_id=int(data["admin_barber_id"]),
            target_date=datetime.fromisoformat(booking_date).date(),
            service_duration_minutes=int(data["reschedule_duration"]),
        )
        await state.update_data(reschedule_date=booking_date)
        if not slots:
            await callback.answer("Bu sanada bo'sh vaqt yo'q.", show_alert=True)
            return
        await state.set_state(RescheduleStates.time)
        await callback.message.edit_text(
            "Yangi vaqtni tanlang:",
            reply_markup=times_keyboard(slots, prefix="adm_move_time"),
        )
        await callback.answer()

    @router.callback_query(RescheduleStates.time, F.data.startswith("adm_move_time:"))
    async def reschedule_time(callback: CallbackQuery, state: FSMContext) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        data = await state.get_data()
        selected_time = callback.data.split(":", maxsplit=1)[1]
        booking_at = datetime.fromisoformat(f"{data['reschedule_date']}T{selected_time}:00").replace(
            tzinfo=repository.timezone
        )
        success = await repository.reschedule_booking(int(data["reschedule_booking_id"]), booking_at)
        await state.clear()
        if not success:
            await callback.answer("Reschedule bajarilmadi.", show_alert=True)
            return
        booking = await repository.get_admin_booking(int(data["reschedule_booking_id"]))
        await callback.message.edit_text(await _booking_card_text(booking), reply_markup=booking_admin_keyboard(booking["id"]))
        await callback.answer("Bron ko'chirildi")

    @router.callback_query(F.data == "adm_sch:pick_barber")
    async def schedule_pick_barber(callback: CallbackQuery) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        barbers = await repository.list_barbers()
        await callback.message.edit_text(
            "Jadval uchun ustani tanlang:",
            reply_markup=barbers_keyboard(barbers, prefix="adm_sch_barber"),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("adm_sch_barber:"))
    async def schedule_barber_selected(callback: CallbackQuery, state: FSMContext) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        barber_id = int(callback.data.split(":", maxsplit=1)[1])
        await state.update_data(admin_barber_id=barber_id)
        await callback.message.edit_text(
            await _render_schedule_text(state),
            reply_markup=schedule_keyboard(barber_id),
        )
        await callback.answer()

    @router.callback_query(F.data == "adm_sch:hours")
    async def schedule_hours(callback: CallbackQuery, state: FSMContext) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        await state.set_state(ScheduleStates.working_hours)
        await callback.message.answer("Yangi ish vaqtini yuboring. Format: 09:00-21:00")
        await callback.answer()

    @router.callback_query(F.data == "adm_sch:break")
    async def schedule_break(callback: CallbackQuery, state: FSMContext) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        await state.set_state(ScheduleStates.break_time)
        await callback.message.answer("Tanaffus vaqtini yuboring. Format: 13:00-14:00 yoki yo'q")
        await callback.answer()

    @router.callback_query(F.data == "adm_sch:offdays")
    async def schedule_offdays(callback: CallbackQuery, state: FSMContext) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        await state.set_state(ScheduleStates.off_days)
        await callback.message.answer("Dam olish kunlarini yuboring. Misol: 0,6 yoki bo'sh")
        await callback.answer()

    @router.callback_query(F.data == "adm_sch:block")
    async def schedule_block(callback: CallbackQuery, state: FSMContext) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        await state.set_state(ScheduleStates.blocked_slot)
        await callback.message.answer("Blok slot kiriting. Format: 2026-04-05 14:00")
        await callback.answer()

    @router.message(ScheduleStates.working_hours)
    async def schedule_hours_save(message: Message, state: FSMContext) -> None:
        if not _message_is_admin(message):
            await _deny_message(message)
            return
        try:
            start_time, end_time = parse_time_range(message.text or "")
        except Exception:
            await message.answer("Format xato. Masalan: 09:00-21:00")
            return
        barber_id = await _selected_barber_id(state)
        await repository.update_schedule_hours(barber_id, start_time, end_time)
        await state.clear()
        await state.update_data(admin_barber_id=barber_id)
        await message.answer(await _render_schedule_text(state), reply_markup=schedule_keyboard(barber_id))

    @router.message(ScheduleStates.break_time)
    async def schedule_break_save(message: Message, state: FSMContext) -> None:
        if not _message_is_admin(message):
            await _deny_message(message)
            return
        raw = (message.text or "").strip().lower()
        if raw in {"yo'q", "yoq", "none", "-"}:
            start_time = end_time = None
        else:
            try:
                start_time, end_time = parse_time_range(message.text or "")
            except Exception:
                await message.answer("Format xato. Masalan: 13:00-14:00 yoki yo'q")
                return
        barber_id = await _selected_barber_id(state)
        await repository.update_schedule_break(barber_id, start_time, end_time)
        await state.clear()
        await state.update_data(admin_barber_id=barber_id)
        await message.answer(await _render_schedule_text(state), reply_markup=schedule_keyboard(barber_id))

    @router.message(ScheduleStates.off_days)
    async def schedule_offdays_save(message: Message, state: FSMContext) -> None:
        if not _message_is_admin(message):
            await _deny_message(message)
            return
        raw = (message.text or "").replace(" ", "")
        if raw:
            valid = all(item.isdigit() and 0 <= int(item) <= 6 for item in raw.split(",") if item)
            if not valid:
                await message.answer("Faqat 0 dan 6 gacha raqamlar kiriting. Misol: 0,6")
                return
        barber_id = await _selected_barber_id(state)
        await repository.update_schedule_off_days(barber_id, raw)
        await state.clear()
        await state.update_data(admin_barber_id=barber_id)
        await message.answer(await _render_schedule_text(state), reply_markup=schedule_keyboard(barber_id))

    @router.message(ScheduleStates.blocked_slot)
    async def schedule_block_save(message: Message, state: FSMContext) -> None:
        if not _message_is_admin(message):
            await _deny_message(message)
            return
        try:
            blocked_at = datetime.strptime((message.text or "").strip(), "%Y-%m-%d %H:%M").replace(
                tzinfo=repository.timezone
            )
        except ValueError:
            await message.answer("Format xato. Masalan: 2026-04-05 14:00")
            return
        barber_id = await _selected_barber_id(state)
        await repository.add_blocked_slot(barber_id, blocked_at, reason="admin_block")
        await state.clear()
        await state.update_data(admin_barber_id=barber_id)
        await message.answer(await _render_schedule_text(state), reply_markup=schedule_keyboard(barber_id))

    @router.callback_query(F.data == "adm_srv:add")
    async def service_add(callback: CallbackQuery, state: FSMContext) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        await state.set_state(ServiceStates.add_name)
        await callback.message.answer("Yangi xizmat nomini yuboring:")
        await callback.answer()

    @router.callback_query(F.data == "adm_srv:edit")
    async def service_edit(callback: CallbackQuery) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        services = await repository.list_services()
        await callback.message.edit_text(
            "Narxini o'zgartirish uchun xizmatni tanlang:",
            reply_markup=service_picker_keyboard(services, "adm_srv_edit"),
        )
        await callback.answer()

    @router.callback_query(F.data == "adm_srv:delete")
    async def service_delete(callback: CallbackQuery) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        services = await repository.list_services()
        await callback.message.edit_text(
            "O'chirish uchun xizmatni tanlang:",
            reply_markup=service_picker_keyboard(services, "adm_srv_del"),
        )
        await callback.answer()

    @router.message(ServiceStates.add_name)
    async def service_add_name(message: Message, state: FSMContext) -> None:
        if not _message_is_admin(message):
            await _deny_message(message)
            return
        await state.update_data(service_name=(message.text or "").strip())
        await state.set_state(ServiceStates.add_description)
        await message.answer("Xizmat tavsifini yuboring:")

    @router.message(ServiceStates.add_description)
    async def service_add_description(message: Message, state: FSMContext) -> None:
        if not _message_is_admin(message):
            await _deny_message(message)
            return
        await state.update_data(service_description=(message.text or "").strip())
        await state.set_state(ServiceStates.add_duration)
        await message.answer("Davomiyligini daqiqada yuboring. Masalan: 60")

    @router.message(ServiceStates.add_duration)
    async def service_add_duration(message: Message, state: FSMContext) -> None:
        if not _message_is_admin(message):
            await _deny_message(message)
            return
        if not (message.text or "").strip().isdigit():
            await message.answer("Davomiylik faqat raqam bo'lishi kerak.")
            return
        await state.update_data(service_duration=int(message.text.strip()))
        await state.set_state(ServiceStates.add_price)
        await message.answer("Narxni so'mda yuboring. Masalan: 90000")

    @router.message(ServiceStates.add_price)
    async def service_add_price(message: Message, state: FSMContext) -> None:
        if not _message_is_admin(message):
            await _deny_message(message)
            return
        if not (message.text or "").strip().isdigit():
            await message.answer("Narx faqat raqam bo'lishi kerak.")
            return
        data = await state.get_data()
        await repository.create_service(
            name=data["service_name"],
            description=data["service_description"],
            duration_minutes=int(data["service_duration"]),
            price=int(message.text.strip()),
        )
        await state.clear()
        await message.answer(await _render_services_text(), reply_markup=service_manage_keyboard())

    @router.callback_query(F.data.startswith("adm_srv_edit:"))
    async def service_edit_pick(callback: CallbackQuery, state: FSMContext) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        service_id = int(callback.data.split(":", maxsplit=1)[1])
        await state.set_state(ServiceStates.edit_price)
        await state.update_data(edit_service_id=service_id)
        await callback.message.answer("Yangi narxni yuboring:")
        await callback.answer()

    @router.message(ServiceStates.edit_price)
    async def service_edit_price_save(message: Message, state: FSMContext) -> None:
        if not _message_is_admin(message):
            await _deny_message(message)
            return
        if not (message.text or "").strip().isdigit():
            await message.answer("Narx faqat raqam bo'lishi kerak.")
            return
        data = await state.get_data()
        await repository.update_service_price(int(data["edit_service_id"]), int(message.text.strip()))
        await state.clear()
        await message.answer(await _render_services_text(), reply_markup=service_manage_keyboard())

    @router.callback_query(F.data.startswith("adm_srv_del:"))
    async def service_delete_pick(callback: CallbackQuery) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        service_id = int(callback.data.split(":", maxsplit=1)[1])
        await repository.deactivate_service(service_id)
        await callback.message.edit_text(await _render_services_text(), reply_markup=service_manage_keyboard())
        await callback.answer("Xizmat o'chirildi")

    @router.callback_query(F.data == "adm_set:shop_name")
    async def settings_shop_name(callback: CallbackQuery, state: FSMContext) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        await state.set_state(SettingsStates.shop_name)
        await callback.message.answer("Yangi shop name yuboring:")
        await callback.answer()

    @router.callback_query(F.data == "adm_set:address")
    async def settings_address(callback: CallbackQuery, state: FSMContext) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        await state.set_state(SettingsStates.address)
        await callback.message.answer("Yangi manzilni yuboring:")
        await callback.answer()

    @router.callback_query(F.data == "adm_set:barber")
    async def settings_barber(callback: CallbackQuery) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        barbers = await repository.list_barbers()
        await callback.message.edit_text(
            "Nomini o'zgartirish uchun ustani tanlang:",
            reply_markup=choose_barber_for_settings_keyboard(barbers, "adm_set_barber"),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("adm_set_barber:"))
    async def settings_barber_pick(callback: CallbackQuery, state: FSMContext) -> None:
        if not _callback_is_admin(callback):
            await _deny_callback(callback)
            return
        barber_id = int(callback.data.split(":", maxsplit=1)[1])
        await state.set_state(SettingsStates.barber_name)
        await state.update_data(rename_barber_id=barber_id)
        await callback.message.answer("Yangi barber name yuboring:")
        await callback.answer()

    @router.message(SettingsStates.shop_name)
    async def settings_shop_name_save(message: Message, state: FSMContext) -> None:
        if not _message_is_admin(message):
            await _deny_message(message)
            return
        await repository.set_shop_setting("shop_name", (message.text or "").strip())
        await state.clear()
        await message.answer(await _render_settings_text(), reply_markup=settings_keyboard())

    @router.message(SettingsStates.address)
    async def settings_address_save(message: Message, state: FSMContext) -> None:
        if not _message_is_admin(message):
            await _deny_message(message)
            return
        await repository.set_shop_setting("address", (message.text or "").strip())
        await state.clear()
        await message.answer(await _render_settings_text(), reply_markup=settings_keyboard())

    @router.message(SettingsStates.barber_name)
    async def settings_barber_name_save(message: Message, state: FSMContext) -> None:
        if not _message_is_admin(message):
            await _deny_message(message)
            return
        data = await state.get_data()
        await repository.rename_barber(int(data["rename_barber_id"]), (message.text or "").strip())
        await state.clear()
        await message.answer(await _render_settings_text(), reply_markup=settings_keyboard())

    return router
