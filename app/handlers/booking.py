from __future__ import annotations

from datetime import date, datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.constants import BOOK_APPOINTMENT
from app.database.repository import Repository
from app.keyboards.inline import (
    barbers_keyboard,
    cancel_booking_keyboard,
    confirm_booking_keyboard,
    dates_keyboard,
    services_keyboard,
    times_keyboard,
)
from app.keyboards.reply import main_menu_keyboard
from app.states.booking import BookingStates
from app.ui import booking_preview_text, booking_success_text, main_menu_hint, send_optional_sticker
from app.utils import format_datetime_uz


def get_booking_router(repository: Repository, settings) -> Router:
    router = Router(name="booking")

    async def _show_barber_step(callback: CallbackQuery, state: FSMContext) -> None:
        barbers = await repository.list_barbers()
        await state.set_state(BookingStates.barber)
        await callback.message.edit_text("👨‍🦱 Ustani tanlang:", reply_markup=barbers_keyboard(barbers))

    async def _show_date_step(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(BookingStates.date)
        await callback.message.edit_text("📅 Sanani tanlang:", reply_markup=dates_keyboard(7, prefix="book_date"))

    @router.message(F.text == BOOK_APPOINTMENT)
    async def start_booking(message: Message, state: FSMContext) -> None:
        if message.from_user:
            await repository.upsert_user(
                telegram_id=message.from_user.id,
                full_name=message.from_user.full_name,
                username=message.from_user.username,
                language_code=message.from_user.language_code,
            )
        services = await repository.list_services()
        await state.clear()
        await state.set_state(BookingStates.service)
        await message.answer("✂️ Xizmat turini tanlang:", reply_markup=services_keyboard(services))

    @router.callback_query(F.data.startswith("rec_book:"))
    async def start_recommended_booking(callback: CallbackQuery, state: FSMContext) -> None:
        service_id = int(callback.data.split(":", maxsplit=1)[1])
        service = await repository.get_service(service_id)
        if not service:
            await callback.answer("Xizmat topilmadi.", show_alert=True)
            return
        await state.clear()
        await state.update_data(service_id=service_id)
        await callback.answer()
        await _show_barber_step(callback, state)

    @router.callback_query(F.data.startswith("prefill_service:"))
    async def prefilled_service(callback: CallbackQuery, state: FSMContext) -> None:
        service_id = int(callback.data.split(":", maxsplit=1)[1])
        data = await state.get_data()
        if "prefill_barber_id" not in data:
            await callback.answer("Usta tanlanmagan.", show_alert=True)
            return
        service = await repository.get_service(service_id)
        if not service:
            await callback.answer("Xizmat topilmadi.", show_alert=True)
            return
        await state.update_data(service_id=service_id, barber_id=data["prefill_barber_id"])
        await callback.answer()
        await _show_date_step(callback, state)

    @router.callback_query(F.data.startswith("book_service:"))
    async def select_service(callback: CallbackQuery, state: FSMContext) -> None:
        service_id = int(callback.data.split(":", maxsplit=1)[1])
        service = await repository.get_service(service_id)
        if not service:
            await callback.answer("Xizmat topilmadi.", show_alert=True)
            return
        await state.update_data(service_id=service_id)
        await callback.answer()
        await _show_barber_step(callback, state)

    @router.callback_query(F.data.startswith("book_barber:"))
    async def select_barber(callback: CallbackQuery, state: FSMContext) -> None:
        barber_id = int(callback.data.split(":", maxsplit=1)[1])
        barber = await repository.get_barber(barber_id)
        if not barber:
            await callback.answer("Usta topilmadi.", show_alert=True)
            return
        await state.update_data(barber_id=barber_id)
        await callback.answer()
        await _show_date_step(callback, state)

    @router.callback_query(F.data.startswith("book_date:"))
    async def select_date(callback: CallbackQuery, state: FSMContext) -> None:
        selected_date = date.fromisoformat(callback.data.split(":", maxsplit=1)[1])
        data = await state.get_data()
        service = await repository.get_service(data["service_id"])
        if not service:
            await callback.answer("Xizmat topilmadi.", show_alert=True)
            return
        slots = await repository.list_available_slots(
            barber_id=data["barber_id"],
            target_date=selected_date,
            service_duration_minutes=service["duration_minutes"],
        )
        await state.update_data(booking_date=selected_date.isoformat())
        await state.set_state(BookingStates.time)
        if not slots:
            await callback.message.edit_text(
                "😕 Bu sana uchun bo'sh vaqt topilmadi. Boshqa sanani tanlang:",
                reply_markup=dates_keyboard(7, prefix="book_date"),
            )
            await callback.answer()
            return
        await callback.message.edit_text("🕒 Bo'sh vaqtni tanlang:", reply_markup=times_keyboard(slots))
        await callback.answer()

    @router.callback_query(F.data.startswith("book_time:"))
    async def select_time(callback: CallbackQuery, state: FSMContext) -> None:
        selected_time = callback.data.split(":", maxsplit=1)[1]
        await state.update_data(booking_time=selected_time)
        data = await state.get_data()
        service = await repository.get_service(data["service_id"])
        barber = await repository.get_barber(data["barber_id"])
        booking_at = datetime.fromisoformat(f"{data['booking_date']}T{selected_time}:00").replace(
            tzinfo=repository.timezone
        )
        await state.set_state(BookingStates.confirm)
        await callback.message.edit_text(
            booking_preview_text(service, barber, format_datetime_uz(booking_at)),
            reply_markup=confirm_booking_keyboard(),
        )
        await callback.answer()

    @router.callback_query(F.data == "book_abort")
    async def abort_booking(callback: CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        await callback.message.edit_text("❌ Bron qilish bekor qilindi.")
        await callback.message.answer(main_menu_hint(), reply_markup=main_menu_keyboard())
        await callback.answer()

    @router.callback_query(F.data == "book_confirm")
    async def confirm_booking(callback: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        service = await repository.get_service(data["service_id"])
        barber = await repository.get_barber(data["barber_id"])
        if not callback.from_user or not service or not barber:
            await callback.answer("Bronni yaratib bo'lmadi.", show_alert=True)
            return

        booking_at = datetime.fromisoformat(f"{data['booking_date']}T{data['booking_time']}:00").replace(
            tzinfo=repository.timezone
        )
        available_slots = await repository.list_available_slots(
            barber_id=barber["id"],
            target_date=booking_at.date(),
            service_duration_minutes=service["duration_minutes"],
        )
        if booking_at.strftime("%H:%M") not in available_slots:
            await state.set_state(BookingStates.time)
            if not available_slots:
                await state.set_state(BookingStates.date)
                await callback.message.edit_text(
                    "😕 Bu vaqt band bo'lib qoldi va boshqa slot qolmadi. Yangi sanani tanlang:",
                    reply_markup=dates_keyboard(7, prefix="book_date"),
                )
            else:
                await callback.message.edit_text(
                    "⏱ Bu vaqt band bo'lib qoldi. Yangi bo'sh vaqtni tanlang:",
                    reply_markup=times_keyboard(available_slots),
                )
            await callback.answer("Jadval yangilandi", show_alert=True)
            return

        booking_id = await repository.create_booking(
            telegram_id=callback.from_user.id,
            service_id=service["id"],
            barber_id=barber["id"],
            booking_at=booking_at,
            total_price=service["price"],
        )
        details = await repository.get_booking_details(booking_id)
        await state.clear()
        await send_optional_sticker(callback.message, settings.booking_sticker_id)
        await callback.message.edit_text(
            booking_success_text(details, booking_id, format_datetime_uz(booking_at)),
            reply_markup=cancel_booking_keyboard(booking_id),
        )
        await callback.message.answer(main_menu_hint(), reply_markup=main_menu_keyboard())
        await callback.answer()

    @router.callback_query(F.data.startswith("user_cancel:"))
    async def cancel_user_booking(callback: CallbackQuery) -> None:
        booking_id = int(callback.data.split(":", maxsplit=1)[1])
        if not callback.from_user:
            await callback.answer("Foydalanuvchi topilmadi.", show_alert=True)
            return
        success = await repository.cancel_booking(booking_id, callback.from_user.id)
        if not success:
            await callback.answer("Bronni bekor qilib bo'lmadi.", show_alert=True)
            return
        await callback.message.edit_text("❌ Bron bekor qilindi.\nBonuslar balansdan qaytarib olindi.")
        await callback.answer("Bron bekor qilindi")

    return router
