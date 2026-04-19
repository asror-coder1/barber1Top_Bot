from __future__ import annotations

from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.database.repository import Repository
from app.keyboards.inline import dates_keyboard
from app.keyboards.reply import main_menu_keyboard


def get_availability_router(repository: Repository) -> Router:
    router = Router(name="availability")

    @router.callback_query(F.data.startswith("availability_barber:"))
    async def select_availability_barber(callback: CallbackQuery, state: FSMContext) -> None:
        barber_id = int(callback.data.split(":", maxsplit=1)[1])
        await state.update_data(barber_id=barber_id)
        await callback.message.edit_text(
            "Sanani tanlang:",
            reply_markup=dates_keyboard(7, prefix="availability_date"),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("availability_date:"))
    async def show_availability(callback: CallbackQuery, state: FSMContext) -> None:
        selected_date = date.fromisoformat(callback.data.split(":", maxsplit=1)[1])
        data = await state.get_data()
        barber = await repository.get_barber(data["barber_id"])
        slots = await repository.list_available_slots(data["barber_id"], selected_date)
        await state.clear()

        if not slots:
            await callback.message.edit_text(
                f"{barber['name']} uchun {selected_date.strftime('%d.%m.%Y')} sanada bo'sh vaqt yo'q."
            )
        else:
            await callback.message.edit_text(
                f"<b>{barber['name']}</b> uchun {selected_date.strftime('%d.%m.%Y')} bo'sh vaqtlar:\n"
                + ", ".join(slots)
            )
        await callback.message.answer("Asosiy menyu:", reply_markup=main_menu_keyboard())
        await callback.answer()

    return router
