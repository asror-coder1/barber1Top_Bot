from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


@dataclass(slots=True)
class Settings:
    bot_token: str
    admin_ids: tuple[int, ...]
    barber_ids: tuple[int, ...]
    timezone: ZoneInfo | timezone
    salon_name: str
    salon_address: str
    salon_latitude: float
    salon_longitude: float
    db_path: Path
    barber_panel_enabled: bool
    barber_panel_database_url: str | None
    redis_url: str | None
    start_sticker_id: str | None
    booking_sticker_id: str | None
    admin_sticker_id: str | None

    @classmethod
    def from_env(cls, base_dir: Path) -> "Settings":
        _load_dotenv(base_dir / ".env")

        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")

        admin_ids_raw = os.getenv("ADMIN_IDS", "")
        admin_ids = tuple(
            int(item.strip())
            for item in admin_ids_raw.split(",")
            if item.strip().isdigit()
        )
        barber_ids_raw = os.getenv("BARBER_IDS", "")
        barber_ids = tuple(
            int(item.strip())
            for item in barber_ids_raw.split(",")
            if item.strip().isdigit()
        )

        timezone_name = os.getenv("TIMEZONE", "Asia/Tashkent").strip()
        db_path = Path(os.getenv("DB_PATH", str(base_dir / "barber_ai.db"))).resolve()

        try:
            tz = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            if timezone_name == "Asia/Tashkent":
                tz = timezone(timedelta(hours=5), name="Asia/Tashkent")
            else:
                raise

        return cls(
            bot_token=token,
            admin_ids=admin_ids,
            barber_ids=barber_ids,
            timezone=tz,
            salon_name=os.getenv("SALON_NAME", "Barber AI Studio").strip(),
            salon_address=os.getenv(
                "SALON_ADDRESS",
                "Toshkent shahri, Chilonzor tumani, Bunyodkor ko'chasi 12",
            ).strip(),
            salon_latitude=float(os.getenv("SALON_LATITUDE", "41.285680")),
            salon_longitude=float(os.getenv("SALON_LONGITUDE", "69.203464")),
            db_path=db_path,
            barber_panel_enabled=os.getenv("BARBER_PANEL_ENABLED", "false").strip().lower() in {"1", "true", "yes"},
            barber_panel_database_url=os.getenv("BARBER_PANEL_DATABASE_URL", "").strip() or None,
            redis_url=os.getenv("REDIS_URL", "").strip() or None,
            start_sticker_id=os.getenv("START_STICKER_ID", "").strip() or None,
            booking_sticker_id=os.getenv("BOOKING_STICKER_ID", "").strip() or None,
            admin_sticker_id=os.getenv("ADMIN_STICKER_ID", "").strip() or None,
        )
