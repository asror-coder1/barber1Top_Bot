from __future__ import annotations

from datetime import date, datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ErrorEvent, Message

from app.barber_panel.application.services import BarberPanelService
from app.barber_panel.domain.exceptions import BarberPanelError, ValidationError
from app.barber_panel.presentation.keyboards.barber_panel import (
    barber_main_keyboard,
    booking_card_keyboard,
    bookings_filter_keyboard,
    chat_threads_keyboard,
    dashboard_keyboard,
    pricing_keyboard,
    profile_keyboard,
    quick_reply_keyboard,
    reschedule_dates_keyboard,
    reschedule_times_keyboard,
    reviews_keyboard,
    schedule_keyboard,
    service_actions_keyboard,
    services_keyboard,
    settings_keyboard,
)
from app.barber_panel.presentation.middlewares.access import BarberAccessMiddleware
from app.barber_panel.presentation.states.barber_panel import (
    BookingStates,
    ChatStates,
    ProfileStates,
    ReviewStates,
    ScheduleStates,
    ServiceStates,
)
from app.barber_panel.presentation.texts.barber_panel import (
    analytics_text,
    booking_card_text,
    chat_inbox_text,
    chat_thread_text,
    dashboard_text,
    pricing_text,
    profile_text,
    reviews_text,
    schedule_text,
    services_text,
    settings_text,
)
from app.utils import parse_time_range


QUICK_REPLIES = {
    "on_my_way": "Assalomu alaykum, yo'ldaman. Tez orada siz bilan bog'lanaman.",
    "ready_soon": "Sizning broningiz 5 daqiqada tayyor bo'ladi.",
    "booking_confirmed": "Bron tasdiqlandi. Sizni kutamiz.",
    "call_me": "Iltimos, qulay paytda menga qo'ng'iroq qiling.",
}


def get_barber_panel_router(service: BarberPanelService) -> Router:
    router = Router(name="barber_panel")
    router.message.middleware(BarberAccessMiddleware(service))
    router.callback_query.middleware(BarberAccessMiddleware(service))

    async def show_dashboard(message: Message) -> None:
        metrics = await service.get_dashboard(message.from_user.id)
        await message.answer(
            dashboard_text(metrics),
            reply_markup=dashboard_keyboard(),
        )

    async def render_bookings(target, telegram_id: int, filter_key: str) -> None:
        cards = await service.list_bookings(telegram_id, filter_key)
        header = "📅 <b>Bronlar</b>\n\nPremium list view"
        if isinstance(target, Message):
            await target.answer(header, reply_markup=bookings_filter_keyboard(filter_key))
            for card in cards:
                await target.answer(booking_card_text(card), reply_markup=booking_card_keyboard(card.booking_id, card.status))
        else:
            await target.message.edit_text(header, reply_markup=bookings_filter_keyboard(filter_key))
            for card in cards:
                await target.message.answer(booking_card_text(card), reply_markup=booking_card_keyboard(card.booking_id, card.status))

    @router.message(Command("barber"))
    async def barber_panel_entry(message: Message) -> None:
        await message.answer(
            "Barber AI barber panel ochildi.",
            reply_markup=barber_main_keyboard(),
        )
        await show_dashboard(message)

    @router.message(F.text == "📅 Bronlar")
    async def bookings_menu(message: Message) -> None:
        await render_bookings(message, message.from_user.id, "today")

    @router.message(F.text == "👤 Profil")
    async def profile_menu(message: Message) -> None:
        profile = await service.get_profile(message.from_user.id)
        await message.answer(profile_text(profile), reply_markup=profile_keyboard())

    @router.message(F.text == "✂️ Xizmatlar")
    async def services_menu(message: Message) -> None:
        services = await service.list_services(message.from_user.id)
        await message.answer(services_text(services), reply_markup=services_keyboard(services))

    @router.message(F.text == "💰 Narxlar")
    async def pricing_menu(message: Message) -> None:
        services = await service.list_services(message.from_user.id)
        await message.answer(pricing_text(services), reply_markup=pricing_keyboard(services))

    @router.message(F.text == "🕒 Ish jadvali")
    async def schedule_menu(message: Message) -> None:
        schedule = await service.get_schedule(message.from_user.id)
        await message.answer(schedule_text(schedule), reply_markup=schedule_keyboard(schedule.working_days, schedule.vacation_mode))

    @router.message(F.text == "⭐ Sharhlar")
    async def reviews_menu(message: Message) -> None:
        summary = await service.get_reviews(message.from_user.id)
        await message.answer(reviews_text(summary), reply_markup=reviews_keyboard(summary.reviews))

    @router.message(F.text == "📈 Statistika")
    async def analytics_menu(message: Message) -> None:
        stats = await service.get_analytics(message.from_user.id)
        await message.answer(analytics_text(stats), reply_markup=dashboard_keyboard())

    @router.message(F.text == "💬 Chat")
    async def chat_menu(message: Message) -> None:
        threads = await service.get_chat_threads(message.from_user.id)
        await message.answer(chat_inbox_text(threads), reply_markup=chat_threads_keyboard(threads))

    @router.message(F.text == "⚙️ Sozlamalar")
    async def settings_menu(message: Message) -> None:
        barber = await service.get_barber_or_raise(message.from_user.id)
        await message.answer(
            settings_text(barber.notifications_enabled, barber.theme),
            reply_markup=settings_keyboard(barber.notifications_enabled),
        )

    @router.callback_query(F.data == "bp:dashboard")
    async def dashboard_callback(callback: CallbackQuery) -> None:
        metrics = await service.get_dashboard(callback.from_user.id)
        await callback.message.edit_text(dashboard_text(metrics), reply_markup=dashboard_keyboard())
        await callback.answer()

    @router.callback_query(F.data == "bp:bookings")
    async def bookings_callback(callback: CallbackQuery) -> None:
        await render_bookings(callback, callback.from_user.id, "today")
        await callback.answer()

    @router.callback_query(F.data.startswith("bp:bookings:"))
    async def bookings_filter_callback(callback: CallbackQuery) -> None:
        filter_key = callback.data.rsplit(":", maxsplit=1)[1]
        await render_bookings(callback, callback.from_user.id, filter_key)
        await callback.answer()

    @router.callback_query(F.data.startswith("bp:booking:"))
    async def booking_action_callback(callback: CallbackQuery, state: FSMContext) -> None:
        _, _, action, booking_id_text = callback.data.split(":")
        booking_id = int(booking_id_text)
        if action == "reschedule":
            await state.set_state(BookingStates.waiting_for_reschedule_date)
            await state.update_data(reschedule_booking_id=booking_id)
            await callback.message.edit_text(
                "Yangi sanani tanlang. Tugmalar `12-aprel` formatida chiqarildi.",
                reply_markup=reschedule_dates_keyboard(),
            )
            await callback.answer()
            return
        card = await service.update_booking_status(callback.from_user.id, booking_id, action)
        await callback.message.edit_text(booking_card_text(card), reply_markup=booking_card_keyboard(card.booking_id, card.status))
        await callback.answer("Yangilandi")

    @router.callback_query(BookingStates.waiting_for_reschedule_date, F.data.startswith("bp:reschedule:date:"))
    async def reschedule_date_callback(callback: CallbackQuery, state: FSMContext) -> None:
        iso_date = callback.data.rsplit(":", maxsplit=1)[1]
        grouped = await service.get_available_reschedule_slots(callback.from_user.id, date.fromisoformat(iso_date))
        await state.update_data(reschedule_date=iso_date)
        await state.set_state(BookingStates.waiting_for_reschedule_time)
        await callback.message.edit_text(
            "Yangi vaqtni tanlang. Soatlar 2 bo'limga ajratildi.",
            reply_markup=reschedule_times_keyboard(grouped),
        )
        await callback.answer()

    @router.callback_query(BookingStates.waiting_for_reschedule_time, F.data.startswith("bp:reschedule:time:"))
    async def reschedule_time_callback(callback: CallbackQuery, state: FSMContext) -> None:
        selected_time = callback.data.rsplit(":", maxsplit=1)[1]
        data = await state.get_data()
        booking_id = int(data["reschedule_booking_id"])
        new_datetime = datetime.fromisoformat(f"{data['reschedule_date']}T{selected_time}:00")
        card = await service.reschedule_booking(callback.from_user.id, booking_id, new_datetime)
        await state.clear()
        await callback.message.edit_text(booking_card_text(card), reply_markup=booking_card_keyboard(card.booking_id, card.status))
        await callback.answer("Bron ko'chirildi")

    @router.callback_query(F.data == "bp:profile")
    async def profile_callback(callback: CallbackQuery) -> None:
        profile = await service.get_profile(callback.from_user.id)
        await callback.message.edit_text(profile_text(profile), reply_markup=profile_keyboard())
        await callback.answer()

    @router.callback_query(F.data.startswith("bp:profile:edit:"))
    async def profile_edit_callback(callback: CallbackQuery, state: FSMContext) -> None:
        field_name = callback.data.rsplit(":", maxsplit=1)[1]
        await state.set_state(ProfileStates.waiting_for_text)
        await state.update_data(profile_field=field_name)
        await callback.message.answer("Yangi qiymatni yuboring.")
        await callback.answer()

    @router.callback_query(F.data == "bp:profile:photo")
    async def profile_photo_callback(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(ProfileStates.waiting_for_profile_photo)
        await callback.message.answer("Profil rasmini yuboring.")
        await callback.answer()

    @router.callback_query(F.data == "bp:profile:portfolio")
    async def portfolio_photo_callback(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(ProfileStates.waiting_for_portfolio_photo)
        await callback.message.answer("Portfolio uchun rasm yuboring.")
        await callback.answer()

    @router.message(ProfileStates.waiting_for_text)
    async def profile_text_save(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        profile = await service.update_profile_field(message.from_user.id, data["profile_field"], message.text or "")
        await state.clear()
        await message.answer(profile_text(profile), reply_markup=profile_keyboard())

    @router.message(ProfileStates.waiting_for_profile_photo, F.photo)
    async def profile_photo_save(message: Message, state: FSMContext) -> None:
        profile = await service.update_profile_photo(message.from_user.id, message.photo[-1].file_id)
        await state.clear()
        await message.answer(profile_text(profile), reply_markup=profile_keyboard())

    @router.message(ProfileStates.waiting_for_portfolio_photo, F.photo)
    async def portfolio_photo_save(message: Message, state: FSMContext) -> None:
        profile = await service.add_portfolio_image(message.from_user.id, message.photo[-1].file_id)
        await state.clear()
        await message.answer(profile_text(profile), reply_markup=profile_keyboard())

    @router.callback_query(F.data == "bp:services")
    async def services_callback(callback: CallbackQuery) -> None:
        services = await service.list_services(callback.from_user.id)
        await callback.message.edit_text(services_text(services), reply_markup=services_keyboard(services))
        await callback.answer()

    @router.callback_query(F.data == "bp:service:add")
    async def service_add_callback(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(ServiceStates.add_name)
        await callback.message.answer("Xizmat nomini yuboring.")
        await callback.answer()

    @router.callback_query(F.data.startswith("bp:service:view:"))
    async def service_pick_callback(callback: CallbackQuery) -> None:
        service_id = int(callback.data.rsplit(":", maxsplit=1)[1])
        await callback.message.edit_text("Xizmat uchun amal tanlang.", reply_markup=service_actions_keyboard(service_id))
        await callback.answer()

    @router.callback_query(F.data.startswith("bp:service:action:"))
    async def service_action_callback(callback: CallbackQuery, state: FSMContext) -> None:
        _, _, _, field_name, service_id_text = callback.data.split(":")
        service_id = int(service_id_text)
        if field_name == "delete":
            services = await service.delete_service(callback.from_user.id, service_id)
            await callback.message.edit_text(services_text(services), reply_markup=services_keyboard(services))
            await callback.answer("Arxivlandi")
            return
        await state.set_state(ServiceStates.edit_value)
        await state.update_data(service_edit_id=service_id, service_edit_field=field_name)
        await callback.message.answer("Yangi qiymatni yuboring.")
        await callback.answer()

    @router.message(ServiceStates.add_name)
    async def service_add_name(message: Message, state: FSMContext) -> None:
        await state.update_data(service_name=message.text or "")
        await state.set_state(ServiceStates.add_description)
        await message.answer("Tavsifni yuboring.")

    @router.message(ServiceStates.add_description)
    async def service_add_description(message: Message, state: FSMContext) -> None:
        await state.update_data(service_description=message.text or "")
        await state.set_state(ServiceStates.add_duration)
        await message.answer("Davomiylikni daqiqada yuboring.")

    @router.message(ServiceStates.add_duration)
    async def service_add_duration(message: Message, state: FSMContext) -> None:
        await state.update_data(service_duration=int(message.text or "0"))
        await state.set_state(ServiceStates.add_price)
        await message.answer("Narxni yuboring.")

    @router.message(ServiceStates.add_price)
    async def service_add_price(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        services = await service.create_service(
            message.from_user.id,
            name=data["service_name"],
            description=data["service_description"],
            duration_minutes=int(data["service_duration"]),
            price=int(message.text or "0"),
        )
        await state.clear()
        await message.answer(services_text(services), reply_markup=services_keyboard(services))

    @router.message(ServiceStates.edit_value)
    async def service_edit_value(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        services = await service.update_service(
            message.from_user.id,
            int(data["service_edit_id"]),
            field_name=data["service_edit_field"],
            value=message.text or "",
        )
        await state.clear()
        await message.answer(services_text(services), reply_markup=services_keyboard(services))

    @router.callback_query(F.data == "bp:pricing")
    async def pricing_callback(callback: CallbackQuery) -> None:
        services = await service.list_services(callback.from_user.id)
        await callback.message.edit_text(pricing_text(services), reply_markup=pricing_keyboard(services))
        await callback.answer()

    @router.callback_query(F.data.startswith("bp:pricing:set:"))
    async def pricing_set_callback(callback: CallbackQuery, state: FSMContext) -> None:
        service_id = int(callback.data.rsplit(":", maxsplit=1)[1])
        await state.set_state(ServiceStates.edit_value)
        await state.update_data(service_edit_id=service_id, service_edit_field="price")
        await callback.message.answer("Yangi narxni yuboring.")
        await callback.answer()

    @router.callback_query(F.data == "bp:pricing:bulk")
    async def pricing_bulk_callback(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(ServiceStates.bulk_price)
        await callback.message.answer("Foiz o'zgarishini yuboring. Masalan: 10 yoki -5")
        await callback.answer()

    @router.message(ServiceStates.bulk_price)
    async def pricing_bulk_save(message: Message, state: FSMContext) -> None:
        services = await service.bulk_update_prices(message.from_user.id, int(message.text or "0"))
        await state.clear()
        await message.answer(pricing_text(services), reply_markup=pricing_keyboard(services))

    @router.callback_query(F.data == "bp:schedule")
    async def schedule_callback(callback: CallbackQuery) -> None:
        schedule = await service.get_schedule(callback.from_user.id)
        await callback.message.edit_text(
            schedule_text(schedule),
            reply_markup=schedule_keyboard(schedule.working_days, schedule.vacation_mode),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("bp:schedule:day:"))
    async def schedule_day_callback(callback: CallbackQuery) -> None:
        weekday_index = int(callback.data.rsplit(":", maxsplit=1)[1])
        schedule = await service.toggle_working_day(callback.from_user.id, weekday_index)
        await callback.message.edit_text(
            schedule_text(schedule),
            reply_markup=schedule_keyboard(schedule.working_days, schedule.vacation_mode),
        )
        await callback.answer()

    @router.callback_query(F.data == "bp:schedule:hours")
    async def schedule_hours_callback(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(ScheduleStates.waiting_for_hours)
        await callback.message.answer("Format: 10:00-21:00")
        await callback.answer()

    @router.callback_query(F.data == "bp:schedule:break")
    async def schedule_break_callback(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(ScheduleStates.waiting_for_break)
        await callback.message.answer("Format: 13:00-14:00 yoki yo'q")
        await callback.answer()

    @router.callback_query(F.data == "bp:schedule:unavailable")
    async def schedule_unavailable_callback(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(ScheduleStates.waiting_for_unavailable_date)
        await callback.message.answer("Band sanani yuboring. Misol: 2026-04-12")
        await callback.answer()

    @router.callback_query(F.data.startswith("bp:schedule:custom:"))
    async def schedule_custom_callback(callback: CallbackQuery, state: FSMContext) -> None:
        slot_type = callback.data.rsplit(":", maxsplit=1)[1]
        target_state = ScheduleStates.waiting_for_custom_open_slot if slot_type == "open" else ScheduleStates.waiting_for_custom_closed_slot
        await state.set_state(target_state)
        await callback.message.answer("Slot yuboring. Misol: 2026-04-12T15:30:00")
        await callback.answer()

    @router.callback_query(F.data == "bp:schedule:vacation")
    async def schedule_vacation_callback(callback: CallbackQuery) -> None:
        schedule = await service.toggle_vacation_mode(callback.from_user.id)
        await callback.message.edit_text(
            schedule_text(schedule),
            reply_markup=schedule_keyboard(schedule.working_days, schedule.vacation_mode),
        )
        await callback.answer("Yangilandi")

    @router.message(ScheduleStates.waiting_for_hours)
    async def schedule_hours_save(message: Message, state: FSMContext) -> None:
        start_at, end_at = parse_time_range(message.text or "")
        schedule = await service.update_schedule_hours(message.from_user.id, start_at, end_at)
        await state.clear()
        await message.answer(schedule_text(schedule), reply_markup=schedule_keyboard(schedule.working_days, schedule.vacation_mode))

    @router.message(ScheduleStates.waiting_for_break)
    async def schedule_break_save(message: Message, state: FSMContext) -> None:
        text = (message.text or "").strip().lower()
        if text in {"yo'q", "yoq", "none", "-"}:
            start_at = end_at = None
        else:
            start_at, end_at = parse_time_range(message.text or "")
        schedule = await service.update_schedule_break(message.from_user.id, start_at, end_at)
        await state.clear()
        await message.answer(schedule_text(schedule), reply_markup=schedule_keyboard(schedule.working_days, schedule.vacation_mode))

    @router.message(ScheduleStates.waiting_for_unavailable_date)
    async def schedule_unavailable_save(message: Message, state: FSMContext) -> None:
        schedule = await service.add_unavailable_date(message.from_user.id, (message.text or "").strip())
        await state.clear()
        await message.answer(schedule_text(schedule), reply_markup=schedule_keyboard(schedule.working_days, schedule.vacation_mode))

    @router.message(ScheduleStates.waiting_for_custom_open_slot)
    async def schedule_open_slot_save(message: Message, state: FSMContext) -> None:
        schedule = await service.add_custom_slot(message.from_user.id, "open", (message.text or "").strip())
        await state.clear()
        await message.answer(schedule_text(schedule), reply_markup=schedule_keyboard(schedule.working_days, schedule.vacation_mode))

    @router.message(ScheduleStates.waiting_for_custom_closed_slot)
    async def schedule_closed_slot_save(message: Message, state: FSMContext) -> None:
        schedule = await service.add_custom_slot(message.from_user.id, "closed", (message.text or "").strip())
        await state.clear()
        await message.answer(schedule_text(schedule), reply_markup=schedule_keyboard(schedule.working_days, schedule.vacation_mode))

    @router.callback_query(F.data == "bp:reviews")
    async def reviews_callback(callback: CallbackQuery) -> None:
        summary = await service.get_reviews(callback.from_user.id)
        await callback.message.edit_text(reviews_text(summary), reply_markup=reviews_keyboard(summary.reviews))
        await callback.answer()

    @router.callback_query(F.data.startswith("bp:review:reply:"))
    async def review_reply_callback(callback: CallbackQuery, state: FSMContext) -> None:
        review_id = int(callback.data.rsplit(":", maxsplit=1)[1])
        await state.set_state(ReviewStates.waiting_for_reply)
        await state.update_data(review_id=review_id)
        await callback.message.answer("Javob matnini yuboring.")
        await callback.answer()

    @router.message(ReviewStates.waiting_for_reply)
    async def review_reply_save(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        summary = await service.reply_to_review(message.from_user.id, int(data["review_id"]), message.text or "")
        await state.clear()
        await message.answer(reviews_text(summary), reply_markup=reviews_keyboard(summary.reviews))

    @router.callback_query(F.data == "bp:analytics")
    async def analytics_callback(callback: CallbackQuery) -> None:
        stats = await service.get_analytics(callback.from_user.id)
        await callback.message.edit_text(analytics_text(stats), reply_markup=dashboard_keyboard())
        await callback.answer()

    @router.callback_query(F.data == "bp:chat")
    async def chat_callback(callback: CallbackQuery) -> None:
        threads = await service.get_chat_threads(callback.from_user.id)
        await callback.message.edit_text(chat_inbox_text(threads), reply_markup=chat_threads_keyboard(threads))
        await callback.answer()

    @router.callback_query(F.data.startswith("bp:chat:thread:"))
    async def chat_thread_callback(callback: CallbackQuery) -> None:
        thread_id = int(callback.data.rsplit(":", maxsplit=1)[1])
        thread, messages = await service.get_chat_thread_messages(callback.from_user.id, thread_id)
        await callback.message.edit_text(chat_thread_text(thread, messages), reply_markup=quick_reply_keyboard(thread.thread_id))
        await callback.answer()

    @router.callback_query(F.data.startswith("bp:chat:quick:"))
    async def chat_quick_reply_callback(callback: CallbackQuery) -> None:
        _, _, _, thread_id_text, reply_key = callback.data.split(":")
        messages = await service.send_quick_reply(callback.from_user.id, int(thread_id_text), QUICK_REPLIES[reply_key])
        thread, _ = await service.get_chat_thread_messages(callback.from_user.id, int(thread_id_text))
        await callback.message.edit_text(chat_thread_text(thread, messages), reply_markup=quick_reply_keyboard(thread.thread_id))
        await callback.answer("Yuborildi")

    @router.callback_query(F.data.startswith("bp:chat:reply:"))
    async def chat_reply_callback(callback: CallbackQuery, state: FSMContext) -> None:
        thread_id = int(callback.data.rsplit(":", maxsplit=1)[1])
        await state.set_state(ChatStates.waiting_for_reply)
        await state.update_data(chat_thread_id=thread_id)
        await callback.message.answer("Javob matnini yuboring.")
        await callback.answer()

    @router.message(ChatStates.waiting_for_reply)
    async def chat_reply_save(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        messages = await service.send_quick_reply(message.from_user.id, int(data["chat_thread_id"]), message.text or "")
        thread, _ = await service.get_chat_thread_messages(message.from_user.id, int(data["chat_thread_id"]))
        await state.clear()
        await message.answer(chat_thread_text(thread, messages), reply_markup=quick_reply_keyboard(thread.thread_id))

    @router.callback_query(F.data == "bp:settings")
    async def settings_callback(callback: CallbackQuery) -> None:
        barber = await service.get_barber_or_raise(callback.from_user.id)
        await callback.message.edit_text(
            settings_text(barber.notifications_enabled, barber.theme),
            reply_markup=settings_keyboard(barber.notifications_enabled),
        )
        await callback.answer()

    @router.callback_query(F.data == "bp:settings:notifications")
    async def settings_notifications_callback(callback: CallbackQuery) -> None:
        notifications_enabled = await service.toggle_notifications(callback.from_user.id)
        barber = await service.get_barber_or_raise(callback.from_user.id)
        await callback.message.edit_text(
            settings_text(notifications_enabled, barber.theme),
            reply_markup=settings_keyboard(notifications_enabled),
        )
        await callback.answer("Toggle saqlandi")

    @router.callback_query(F.data == "bp:settings:theme")
    async def settings_theme_callback(callback: CallbackQuery) -> None:
        theme = await service.toggle_theme(callback.from_user.id)
        barber = await service.get_barber_or_raise(callback.from_user.id)
        await callback.message.edit_text(
            settings_text(barber.notifications_enabled, theme),
            reply_markup=settings_keyboard(barber.notifications_enabled),
        )
        await callback.answer("Tema yangilandi")

    @router.callback_query(F.data == "bp:noop")
    async def noop_callback(callback: CallbackQuery) -> None:
        await callback.answer()

    @router.error()
    async def on_error(event: ErrorEvent) -> bool:
        if isinstance(event.exception, (BarberPanelError, ValidationError)):
            message = getattr(event.update, "message", None)
            callback = getattr(event.update, "callback_query", None)
            if message:
                await message.answer(str(event.exception))
                return True
            if callback:
                await callback.answer(str(event.exception), show_alert=True)
                return True
        return False

    return router
