from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.barber_panel.application.services import BarberPanelService
from app.barber_panel.presentation.handlers.barber_panel import get_barber_panel_router
from app.config import Settings


@dataclass(slots=True)
class BarberPanelRuntime:
    router: object
    engine: AsyncEngine
    redis: Redis | None

    async def close(self) -> None:
        if self.redis is not None:
            await self.redis.close()
        await self.engine.dispose()


async def bootstrap_barber_panel(settings: Settings) -> BarberPanelRuntime | None:
    if not settings.barber_panel_enabled or not settings.barber_panel_database_url:
        return None

    engine = create_async_engine(
        settings.barber_panel_database_url,
        pool_pre_ping=True,
        future=True,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    redis = Redis.from_url(settings.redis_url) if settings.redis_url else None

    def now_local() -> datetime:
        return datetime.now(settings.timezone)

    service = BarberPanelService(
        session_factory=session_factory,
        redis=redis,
        timezone_now=now_local,
        allowed_ids=set(settings.barber_ids),
    )
    return BarberPanelRuntime(
        router=get_barber_panel_router(service),
        engine=engine,
        redis=redis,
    )
