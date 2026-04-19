from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.barber_panel.application.services import BarberPanelService


class BarberAccessMiddleware(BaseMiddleware):
    def __init__(self, service: BarberPanelService) -> None:
        self._service = service

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)

        allowed = await self._service.has_access(user.id)
        if allowed:
            data["barber_panel_service"] = self._service
            return await handler(event, data)

        if isinstance(event, Message):
            await event.answer("Bu bo'lim faqat tasdiqlangan barberlar uchun ochiq.")
            return None
        if isinstance(event, CallbackQuery):
            await event.answer("Ruxsat yo'q", show_alert=True)
            return None
        return None
