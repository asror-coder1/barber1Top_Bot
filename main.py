from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from app.config import Settings
from app.database.repository import Repository
from app.handlers.admin import get_admin_router
from app.handlers.availability import get_availability_router
from app.handlers.barber import get_local_barber_router
from app.handlers.booking import get_booking_router
from app.handlers.common import get_common_router
from app.handlers.recommendation import get_recommendation_router
from app.handlers.review import get_review_router
from app.services.recommendation_engine import RecommendationEngine
from app.services.reminder import ReminderService


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    base_dir = Path(__file__).resolve().parent
    settings = Settings.from_env(base_dir)
    repository = Repository(settings.db_path, settings.timezone)
    await repository.initialize()
    barber_panel_runtime = None
    if settings.barber_panel_enabled:
        from app.barber_panel.bootstrap import bootstrap_barber_panel

        barber_panel_runtime = await bootstrap_barber_panel(settings)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Asosiy menyu"),
            BotCommand(command="help", description="Foydalanish yo'riqnomasi"),
            BotCommand(command="panel", description="Admin panel"),
            BotCommand(command="bookings", description="Bugungi navbatlar"),
            BotCommand(command="customers", description="Mijozlar"),
            BotCommand(command="revenue", description="Daromad"),
            BotCommand(command="schedule", description="Jadval"),
            BotCommand(command="services", description="Xizmatlar"),
            BotCommand(command="reviews", description="Sharhlar"),
            BotCommand(command="settings", description="Sozlamalar"),
            BotCommand(command="barber", description="Barber panel"),
            BotCommand(command="barber_requests", description="Barber arizalari"),
        ]
    )

    dispatcher = Dispatcher()
    dispatcher.include_router(get_admin_router(repository, settings))
    if barber_panel_runtime is not None:
        dispatcher.include_router(barber_panel_runtime.router)
    dispatcher.include_router(get_booking_router(repository, settings))
    dispatcher.include_router(get_availability_router(repository))
    dispatcher.include_router(get_review_router(repository))
    dispatcher.include_router(get_recommendation_router(repository, RecommendationEngine()))
    dispatcher.include_router(get_local_barber_router(repository, settings))
    dispatcher.include_router(get_common_router(repository, settings))

    reminder_service = ReminderService(bot, repository)
    await reminder_service.start()
    try:
        await dispatcher.start_polling(bot)
    finally:
        await reminder_service.stop()
        if barber_panel_runtime is not None:
            await barber_panel_runtime.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
