from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.database.repository import Repository
from app.keyboards.reply import main_menu_keyboard
from app.states.review import ReviewStates


def get_review_router(repository: Repository) -> Router:
    router = Router(name="review")

    @router.callback_query(F.data.startswith("review_rating:"))
    async def receive_rating(callback: CallbackQuery, state: FSMContext) -> None:
        rating = int(callback.data.split(":", maxsplit=1)[1])
        await state.update_data(rating=rating)
        await state.set_state(ReviewStates.comment)
        await callback.message.edit_text("Izoh qoldiring. Agar izoh yo'q bo'lsa, '-' yuboring.")
        await callback.answer()

    @router.message(ReviewStates.comment)
    async def receive_comment(message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        data = await state.get_data()
        comment = "" if (message.text or "").strip() == "-" else (message.text or "").strip()
        await repository.create_review(message.from_user.id, data["rating"], comment)
        await state.clear()
        await message.answer(
            "Sharhingiz uchun rahmat. Fikringiz xizmat sifatini yaxshilashga yordam beradi.",
            reply_markup=main_menu_keyboard(),
        )

    return router
