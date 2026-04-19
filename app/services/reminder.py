from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime, timedelta

from aiogram import Bot

from app.database.repository import Repository
from app.utils import format_datetime_uz, now_local

logger = logging.getLogger(__name__)


class ReminderService:
    def __init__(self, bot: Bot, repository: Repository) -> None:
        self.bot = bot
        self.repository = repository
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="barber-ai-reminders")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _run(self) -> None:
        while True:
            try:
                now = now_local(self.repository.timezone)
                lower_bound = now + timedelta(minutes=25)
                upper_bound = now + timedelta(minutes=35)

                customer_reminders = await self.repository.list_due_customer_reminders(lower_bound, upper_bound)
                for item in customer_reminders:
                    booking_time = format_datetime_uz(datetime.fromisoformat(item["booking_at"]))
                    text = (
                        "⏰ Eslatma\n\n"
                        "Sizning navbatingiz 30 daqiqadan keyin.\n"
                        f"Xizmat: {item['service_name']}\n"
                        f"Usta: {item['barber_name']}\n"
                        f"Vaqt: {booking_time}"
                    )
                    await self.bot.send_message(chat_id=item["telegram_id"], text=text)
                    await self.repository.mark_customer_reminder_sent(item["id"])

                barber_reminders = await self.repository.list_due_barber_reminders(lower_bound, upper_bound)
                for item in barber_reminders:
                    booking_time = format_datetime_uz(datetime.fromisoformat(item["booking_at"]))
                    text = (
                        "🔔 Signal xabar\n\n"
                        "30 daqiqadan keyin klientingiz bor.\n"
                        f"Mijoz: {item['full_name']}\n"
                        f"Telefon: {item['phone']}\n"
                        f"Xizmat: {item['service_name']}\n"
                        f"Vaqt: {booking_time}"
                    )
                    await self.bot.send_message(chat_id=item["telegram_id"], text=text)
                    await self.repository.mark_barber_reminder_sent(item["id"])
            except Exception:  # pragma: no cover
                logger.exception("Reminder loop failed")

            await asyncio.sleep(60)
