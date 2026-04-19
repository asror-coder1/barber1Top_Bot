from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.database.repository import Repository
from app.keyboards.inline import (
    beard_style_keyboard,
    face_shape_keyboard,
    hair_length_keyboard,
    maintenance_keyboard,
    recommendation_card_keyboard,
    style_goal_keyboard,
)
from app.keyboards.reply import main_menu_keyboard
from app.services.recommendation_engine import RecommendationEngine, RecommendationRequest
from app.states.recommendation import RecommendationStates


def get_recommendation_router(repository: Repository, engine: RecommendationEngine) -> Router:
    router = Router(name="recommendation")

    def _parse_channel_post(raw_url: str) -> tuple[str, int] | None:
        match = re.search(r"t\.me/([A-Za-z0-9_]+)/(\d+)", raw_url)
        if not match:
            return None
        return f"@{match.group(1)}", int(match.group(2))

    @router.message(RecommendationStates.photo, F.photo)
    async def receive_selfie(message: Message, state: FSMContext) -> None:
        largest_photo = message.photo[-1]
        await state.update_data(photo_file_id=largest_photo.file_id)
        await state.set_state(RecommendationStates.face_shape)
        await message.answer(
            "Selfie qabul qilindi. Endi yuz shaklingizga eng yaqin variantni tanlang:",
            reply_markup=face_shape_keyboard(),
        )

    @router.message(RecommendationStates.photo)
    async def reject_non_photo(message: Message) -> None:
        await message.answer(
            "Iltimos, yuzingiz aniq ko'rinadigan selfie yuboring. Frontal va yaxshi yorug'likdagi rasm eng yaxshi natija beradi."
        )

    @router.callback_query(RecommendationStates.face_shape, F.data.startswith("rec_face:"))
    async def receive_face_shape(callback: CallbackQuery, state: FSMContext) -> None:
        face_shape = callback.data.split(":", maxsplit=1)[1]
        await state.update_data(face_shape=face_shape)
        await state.set_state(RecommendationStates.hair_length)
        await callback.message.edit_text(
            "Hozirgi soch uzunligingizni tanlang:",
            reply_markup=hair_length_keyboard(),
        )
        await callback.answer()

    @router.callback_query(RecommendationStates.hair_length, F.data.startswith("rec_length:"))
    async def receive_hair_length(callback: CallbackQuery, state: FSMContext) -> None:
        hair_length = callback.data.split(":", maxsplit=1)[1]
        await state.update_data(hair_length=hair_length)
        await state.set_state(RecommendationStates.preferred_style)
        await callback.message.edit_text(
            "Qaysi image sizga yaqinroq:",
            reply_markup=style_goal_keyboard(),
        )
        await callback.answer()

    @router.callback_query(RecommendationStates.preferred_style, F.data.startswith("rec_style:"))
    async def receive_preferred_style(callback: CallbackQuery, state: FSMContext) -> None:
        style_goal = callback.data.split(":", maxsplit=1)[1]
        await state.update_data(preferred_style=style_goal)
        await state.set_state(RecommendationStates.maintenance)
        await callback.message.edit_text(
            "Har kuni styling va parvarishga qancha vaqt ajrata olasiz?",
            reply_markup=maintenance_keyboard(),
        )
        await callback.answer()

    @router.callback_query(RecommendationStates.maintenance, F.data.startswith("rec_maintenance:"))
    async def receive_maintenance(callback: CallbackQuery, state: FSMContext) -> None:
        maintenance_level = callback.data.split(":", maxsplit=1)[1]
        await state.update_data(maintenance=maintenance_level)
        await state.set_state(RecommendationStates.beard_style)
        await callback.message.edit_text(
            "Soqol bilan qanday kombinatsiya xohlaysiz?",
            reply_markup=beard_style_keyboard(),
        )
        await callback.answer()

    @router.callback_query(RecommendationStates.beard_style, F.data.startswith("rec_beard:"))
    async def receive_beard_style(callback: CallbackQuery, state: FSMContext) -> None:
        beard_style = callback.data.split(":", maxsplit=1)[1]
        await state.update_data(beard_style=beard_style)
        data = await state.get_data()

        catalog = await repository.list_hairstyle_catalog()
        request = RecommendationRequest(
            face_shape=data["face_shape"],
            hair_length=data["hair_length"],
            style_goal=data["preferred_style"],
            maintenance_level=data["maintenance"],
            beard_style=beard_style,
            has_selfie=bool(data.get("photo_file_id")),
        )
        recommendations = engine.recommend(request, catalog)

        persistable_results: list[dict[str, str | int]] = []
        for item in recommendations:
            persistable_results.append(
                {
                    "slug": item.slug,
                    "name": item.name,
                    "score": item.score,
                    "booking_service_name": item.booking_service_name,
                    "image_url": item.image_url,
                    "match_reason": item.match_reason,
                }
            )

        if callback.from_user and data.get("photo_file_id"):
            await repository.create_style_consultation(
                telegram_id=callback.from_user.id,
                photo_file_id=data["photo_file_id"],
                face_shape=data["face_shape"],
                hair_length=data["hair_length"],
                style_goal=data["preferred_style"],
                maintenance_level=data["maintenance"],
                beard_style=beard_style,
                recommendations=persistable_results,
            )

        await state.clear()
        await callback.message.edit_text(
            (
                "<b>AI style consultation tayyor</b>\n\n"
                f"Yuz shakli: <b>{data['face_shape']}</b>\n"
                f"Soch uzunligi: <b>{data['hair_length']}</b>\n"
                f"Yo'nalish: <b>{data['preferred_style']}</b>\n"
                f"Parvarish: <b>{data['maintenance']}</b>\n"
                f"Soqol: <b>{beard_style}</b>\n\n"
                "Pastda sizga eng mos 4 ta look chiqdi."
            )
        )

        for index, item in enumerate(recommendations, start=1):
            service = await repository.get_service_by_name(item.booking_service_name)
            post_ref = _parse_channel_post(item.image_url)
            if post_ref is not None:
                await callback.bot.copy_message(
                    chat_id=callback.message.chat.id,
                    from_chat_id=post_ref[0],
                    message_id=post_ref[1],
                )
            await callback.message.answer(
                (
                    f"<b>{index}. {item.name}</b>\n"
                    f"{item.summary}\n\n"
                    f"Nega mos: {item.match_reason}.\n"
                    f"Parvarish: <b>{item.maintenance_level}</b>\n"
                    f"Tavsiya etiladigan xizmat: <b>{item.booking_service_name}</b>"
                ),
                reply_markup=recommendation_card_keyboard(service_id=service["id"] if service else None),
            )

        await callback.message.answer(
            "Agar xohlasangiz, yuqoridagi variantlardan birini bron qilish yoki menyuga qaytish mumkin.",
            reply_markup=main_menu_keyboard(),
        )
        await callback.answer()

    return router
