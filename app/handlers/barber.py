from __future__ import annotations

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.database.repository import Repository
from app.keyboards.reply import barber_panel_keyboard, main_menu_keyboard
from app.utils import format_datetime_uz, format_money, now_local


def get_local_barber_router(repository: Repository, settings) -> Router:
    router = Router(name="local_barber")

    async def _resolve_barber(message: Message) -> dict | None:
        if not message.from_user:
            return None
        return await repository.get_barber_by_telegram_id(message.from_user.id)

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
        if barber is None:
            return
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

    @router.message(F.text == "👤 Mening profilim")
    async def profile(message: Message) -> None:
        barber = await _require_barber(message)
        if barber is None:
            return
        await message.answer(
            (
                f"<b>{barber['name']}</b>\n"
                f"Yo'nalish: {barber['specialty']}\n"
                f"Tajriba: {barber['experience_years']} yil\n"
                f"Telefon: {barber['phone'] or '-'}\n"
                f"Bio: {barber['bio'] or '-'}"
            ),
            reply_markup=barber_panel_keyboard(),
        )

    return router
