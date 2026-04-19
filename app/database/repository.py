from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import aiosqlite

from app.constants import BUSINESS_HOURS, DEFAULT_BARBERS, DEFAULT_SERVICES
from app.utils import now_local, start_of_month, start_of_week


class Repository:
    def __init__(self, db_path: Path, timezone: ZoneInfo) -> None:
        self.db_path = db_path
        self.timezone = timezone

    async def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(
                """
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL UNIQUE,
                    full_name TEXT NOT NULL,
                    username TEXT,
                    language_code TEXT DEFAULT 'uz',
                    phone TEXT,
                    loyalty_points INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS barbers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    specialty TEXT NOT NULL,
                    experience_years INTEGER NOT NULL,
                    telegram_id INTEGER UNIQUE,
                    username TEXT,
                    phone TEXT,
                    bio TEXT,
                    photo_file_id TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS services (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    price INTEGER NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    service_id INTEGER NOT NULL,
                    barber_id INTEGER NOT NULL,
                    booking_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'confirmed',
                    total_price INTEGER NOT NULL,
                    bonus_points_awarded INTEGER NOT NULL DEFAULT 0,
                    reminder_sent_at TEXT,
                    barber_reminder_sent_at TEXT,
                    completed_at TEXT,
                    cancel_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (service_id) REFERENCES services(id),
                    FOREIGN KEY (barber_id) REFERENCES barbers(id)
                );

                CREATE TABLE IF NOT EXISTS bonus_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    booking_id INTEGER,
                    points_delta INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (booking_id) REFERENCES bookings(id)
                );

                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    rating INTEGER NOT NULL,
                    comment TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS payment_intents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    booking_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    provider TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    reference TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (booking_id) REFERENCES bookings(id)
                );

                CREATE TABLE IF NOT EXISTS shop_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS barber_schedules (
                    barber_id INTEGER PRIMARY KEY,
                    work_start TEXT NOT NULL DEFAULT '09:00',
                    work_end TEXT NOT NULL DEFAULT '21:00',
                    break_start TEXT,
                    break_end TEXT,
                    off_days TEXT DEFAULT '',
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (barber_id) REFERENCES barbers(id)
                );

                CREATE TABLE IF NOT EXISTS blocked_slots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    barber_id INTEGER NOT NULL,
                    blocked_at TEXT NOT NULL,
                    reason TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(barber_id, blocked_at),
                    FOREIGN KEY (barber_id) REFERENCES barbers(id)
                );

                CREATE TABLE IF NOT EXISTS hairstyle_catalog (
                    slug TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    face_shapes TEXT NOT NULL,
                    hair_lengths TEXT NOT NULL,
                    style_goals TEXT NOT NULL,
                    maintenance_level TEXT NOT NULL,
                    beard_styles TEXT NOT NULL,
                    booking_service_name TEXT NOT NULL,
                    reference_url TEXT NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    is_active INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS style_consultations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    photo_file_id TEXT NOT NULL,
                    face_shape TEXT NOT NULL,
                    hair_length TEXT NOT NULL,
                    style_goal TEXT NOT NULL,
                    maintenance_level TEXT NOT NULL,
                    beard_style TEXT NOT NULL,
                    recommendations_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS barber_applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL UNIQUE,
                    full_name TEXT NOT NULL,
                    username TEXT,
                    phone TEXT NOT NULL,
                    specialty TEXT NOT NULL,
                    experience_years INTEGER NOT NULL,
                    photo_file_id TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    reviewed_at TEXT,
                    approved_barber_id INTEGER,
                    FOREIGN KEY (approved_barber_id) REFERENCES barbers(id)
                );
                """
            )
            await db.commit()
            await self._ensure_column(db, "users", "phone", "TEXT")
            await self._ensure_column(db, "bookings", "completed_at", "TEXT")
            await self._ensure_column(db, "bookings", "cancel_reason", "TEXT")
            await self._ensure_column(db, "bookings", "barber_reminder_sent_at", "TEXT")
            await self._ensure_column(db, "barbers", "telegram_id", "INTEGER")
            await self._ensure_column(db, "barbers", "username", "TEXT")
            await self._ensure_column(db, "barbers", "phone", "TEXT")
            await self._ensure_column(db, "barbers", "bio", "TEXT")
            await self._ensure_column(db, "barbers", "photo_file_id", "TEXT")
        await self.seed_reference_data()

    async def _ensure_column(self, db: aiosqlite.Connection, table: str, column: str, column_type: str) -> None:
        cursor = await db.execute(f"PRAGMA table_info({table})")
        columns = await cursor.fetchall()
        existing = {row[1] for row in columns}
        if column not in existing:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
            await db.commit()

    async def seed_reference_data(self) -> None:
        timestamp = now_local(self.timezone).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            barber_cursor = await db.execute("SELECT id FROM barbers LIMIT 1")
            if not await barber_cursor.fetchall():
                await db.executemany(
                    """
                    INSERT INTO barbers (name, specialty, experience_years)
                    VALUES (:name, :specialty, :experience_years)
                    """,
                    DEFAULT_BARBERS,
                )
            service_cursor = await db.execute("SELECT id FROM services LIMIT 1")
            if not await service_cursor.fetchall():
                await db.executemany(
                    """
                    INSERT INTO services (name, description, duration_minutes, price)
                    VALUES (:name, :description, :duration_minutes, :price)
                    """,
                    DEFAULT_SERVICES,
                )
            for key, value in {
                "shop_name": "Barber AI Studio",
                "address": "Toshkent shahri, Chilonzor tumani, Bunyodkor ko'chasi 12",
            }.items():
                await db.execute(
                    """
                    INSERT OR IGNORE INTO shop_settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                    """,
                    (key, value, timestamp),
                )
            barber_ids_cursor = await db.execute("SELECT id FROM barbers")
            for row in await barber_ids_cursor.fetchall():
                await db.execute(
                    """
                    INSERT OR IGNORE INTO barber_schedules (
                        barber_id, work_start, work_end, break_start, break_end, off_days, updated_at
                    )
                    VALUES (?, '09:00', '21:00', NULL, NULL, '', ?)
                    """,
                    (row["id"], timestamp),
                )
            await db.executemany(
                """
                INSERT OR REPLACE INTO hairstyle_catalog (
                    slug, name, summary, face_shapes, hair_lengths, style_goals,
                    maintenance_level, beard_styles, booking_service_name, reference_url,
                    sort_order, is_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                [
                    (
                        "textured_crop_fade",
                        "Textured crop fade",
                        "Tepa qismi teksturali, yonlari esa toza fade bilan ishlangan zamonaviy cut.",
                        "Oval,Dumaloq,To'rtburchak",
                        "Qisqa,O'rtacha",
                        "Zamonaviy va trend,Minimal parvarish",
                        "Past",
                        "Toza qirilgan,Qisqa stubble",
                        "Skin fade",
                        "https://t.me/uzbek_frontend7/142",
                        10,
                    ),
                    (
                        "mid_taper_side_part",
                        "Mid taper side part",
                        "Ofis va kundalik hayot uchun muvozanatli, tartibli va toza ko'rinish beradi.",
                        "Oval,Uzunchoq,Yuraksimon",
                        "Qisqa,O'rtacha",
                        "Clean va office,Premium va elegant",
                        "O'rta",
                        "Toza qirilgan,Qisqa stubble,To'liq soqol",
                        "Classic haircut",
                        "https://t.me/uzbek_frontend7/143",
                        20,
                    ),
                    (
                        "classic_pompadour",
                        "Classic pompadour fade",
                        "Hajmli ustki qism va silliq o'tish premium ko'rinish beradi.",
                        "Oval,Yuraksimon,To'rtburchak",
                        "O'rtacha,Uzun",
                        "Premium va elegant,Creative va ajralib turadigan",
                        "Yuqori",
                        "Qisqa stubble,To'liq soqol",
                        "VIP styling",
                        "https://t.me/uzbek_frontend7/144",
                        30,
                    ),
                    (
                        "buzz_cut_beard",
                        "Buzz cut with beard balance",
                        "Keskin va juda toza, yuz chiziqlari aniq ko'rinadigan low-maintenance variant.",
                        "Oval,Dumaloq,To'rtburchak,Uzunchoq",
                        "Qisqa",
                        "Minimal parvarish,Clean va office",
                        "Past",
                        "Qisqa stubble,To'liq soqol",
                        "Haircut + beard",
                        "https://t.me/uzbek_frontend7/145",
                        40,
                    ),
                    (
                        "quiff_taper",
                        "Quiff taper",
                        "Old qismi balandroq, yonlari toza taper bo'lgan balansli fashionable look.",
                        "Oval,Yuraksimon,Uzunchoq",
                        "O'rtacha",
                        "Zamonaviy va trend,Premium va elegant",
                        "O'rta",
                        "Toza qirilgan,Qisqa stubble",
                        "Classic haircut",
                        "https://t.me/uzbek_frontend7/146",
                        50,
                    ),
                    (
                        "crew_cut_taper",
                        "Crew cut taper",
                        "Sportiv, toza va tez stil beriladigan universal qisqa soch varianti.",
                        "Oval,Dumaloq,To'rtburchak",
                        "Qisqa",
                        "Clean va office,Minimal parvarish",
                        "Past",
                        "Toza qirilgan,Qisqa stubble",
                        "Classic haircut",
                        "https://t.me/uzbek_frontend7/147",
                        60,
                    ),
                ],
            )
            await db.commit()

    async def upsert_user(
        self,
        telegram_id: int,
        full_name: str,
        username: str | None,
        language_code: str | None,
        phone: str | None = None,
    ) -> None:
        timestamp = now_local(self.timezone).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO users (
                    telegram_id, full_name, username, language_code, phone, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    full_name = excluded.full_name,
                    username = excluded.username,
                    language_code = excluded.language_code,
                    phone = COALESCE(excluded.phone, users.phone),
                    updated_at = excluded.updated_at
                """,
                (
                    telegram_id,
                    full_name,
                    username,
                    language_code or "uz",
                    phone,
                    timestamp,
                    timestamp,
                ),
            )
            await db.commit()

    async def get_user_profile(self, telegram_id: int) -> dict[str, Any] | None:
        return await self._fetch_one(
            """
            SELECT id, telegram_id, full_name, username, language_code, phone, loyalty_points
            FROM users
            WHERE telegram_id = ?
            """,
            (telegram_id,),
        )

    async def update_user_phone(self, telegram_id: int, phone: str) -> None:
        await self._execute(
            "UPDATE users SET phone = ?, updated_at = ? WHERE telegram_id = ?",
            (phone, now_local(self.timezone).isoformat(), telegram_id),
        )

    async def list_services(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        query = """
            SELECT id, name, description, duration_minutes, price, is_active
            FROM services
        """
        if not include_inactive:
            query += " WHERE is_active = 1"
        query += " ORDER BY price ASC, name ASC"
        return await self._fetch_all(query)

    async def get_service_by_name(self, service_name: str) -> dict[str, Any] | None:
        return await self._fetch_one(
            """
            SELECT id, name, description, duration_minutes, price, is_active
            FROM services
            WHERE name = ? AND is_active = 1
            """,
            (service_name,),
        )

    async def get_service(self, service_id: int) -> dict[str, Any] | None:
        return await self._fetch_one(
            """
            SELECT id, name, description, duration_minutes, price, is_active
            FROM services
            WHERE id = ?
            """,
            (service_id,),
        )

    async def create_service(self, name: str, description: str, duration_minutes: int, price: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO services (name, description, duration_minutes, price, is_active)
                VALUES (?, ?, ?, ?, 1)
                """,
                (name, description, duration_minutes, price),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def update_service_price(self, service_id: int, price: int) -> None:
        await self._execute("UPDATE services SET price = ? WHERE id = ?", (price, service_id))

    async def deactivate_service(self, service_id: int) -> None:
        await self._execute("UPDATE services SET is_active = 0 WHERE id = ?", (service_id,))

    async def list_barbers(self) -> list[dict[str, Any]]:
        return await self._fetch_all(
            """
            SELECT id, name, specialty, experience_years, telegram_id, username, phone, bio, photo_file_id
            FROM barbers
            WHERE is_active = 1
            ORDER BY name ASC
            """
        )

    async def get_barber(self, barber_id: int) -> dict[str, Any] | None:
        return await self._fetch_one(
            """
            SELECT id, name, specialty, experience_years, telegram_id, username, phone, bio, photo_file_id
            FROM barbers
            WHERE id = ?
            """,
            (barber_id,),
        )

    async def get_barber_by_telegram_id(self, telegram_id: int) -> dict[str, Any] | None:
        return await self._fetch_one(
            """
            SELECT id, name, specialty, experience_years, telegram_id, username, phone, bio, photo_file_id
            FROM barbers
            WHERE telegram_id = ? AND is_active = 1
            """,
            (telegram_id,),
        )

    async def rename_barber(self, barber_id: int, new_name: str) -> None:
        await self._execute("UPDATE barbers SET name = ? WHERE id = ?", (new_name, barber_id))

    async def update_barber_profile(self, barber_id: int, *, specialty: str, phone: str | None, bio: str | None) -> None:
        await self._execute(
            """
            UPDATE barbers
            SET specialty = ?, phone = ?, bio = ?
            WHERE id = ?
            """,
            (specialty, phone, bio, barber_id),
        )

    async def get_shop_profile(self, default_shop_name: str, default_address: str) -> dict[str, str]:
        settings = await self._fetch_all("SELECT key, value FROM shop_settings")
        mapping = {item["key"]: item["value"] for item in settings}
        return {
            "shop_name": mapping.get("shop_name", default_shop_name),
            "address": mapping.get("address", default_address),
        }

    async def set_shop_setting(self, key: str, value: str) -> None:
        timestamp = now_local(self.timezone).isoformat()
        await self._execute(
            """
            INSERT INTO shop_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, value, timestamp),
        )

    async def get_schedule(self, barber_id: int) -> dict[str, Any] | None:
        return await self._fetch_one(
            """
            SELECT barber_id, work_start, work_end, break_start, break_end, off_days, updated_at
            FROM barber_schedules
            WHERE barber_id = ?
            """,
            (barber_id,),
        )

    async def update_schedule_hours(self, barber_id: int, work_start: str, work_end: str) -> None:
        await self._execute(
            """
            UPDATE barber_schedules
            SET work_start = ?, work_end = ?, updated_at = ?
            WHERE barber_id = ?
            """,
            (work_start, work_end, now_local(self.timezone).isoformat(), barber_id),
        )

    async def update_schedule_break(self, barber_id: int, break_start: str | None, break_end: str | None) -> None:
        await self._execute(
            """
            UPDATE barber_schedules
            SET break_start = ?, break_end = ?, updated_at = ?
            WHERE barber_id = ?
            """,
            (break_start, break_end, now_local(self.timezone).isoformat(), barber_id),
        )

    async def update_schedule_off_days(self, barber_id: int, off_days: str) -> None:
        await self._execute(
            """
            UPDATE barber_schedules
            SET off_days = ?, updated_at = ?
            WHERE barber_id = ?
            """,
            (off_days, now_local(self.timezone).isoformat(), barber_id),
        )

    async def add_blocked_slot(self, barber_id: int, blocked_at: datetime, reason: str | None = None) -> None:
        await self._execute(
            """
            INSERT OR REPLACE INTO blocked_slots (barber_id, blocked_at, reason, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (barber_id, blocked_at.isoformat(), reason, now_local(self.timezone).isoformat()),
        )

    async def list_blocked_slots(self, barber_id: int, day: date) -> list[str]:
        rows = await self._fetch_all(
            """
            SELECT blocked_at
            FROM blocked_slots
            WHERE barber_id = ? AND date(blocked_at) = ?
            ORDER BY blocked_at ASC
            """,
            (barber_id, day.isoformat()),
        )
        return [datetime.fromisoformat(item["blocked_at"]).strftime("%H:%M") for item in rows]

    async def list_available_slots(
        self,
        barber_id: int,
        target_date: date,
        service_duration_minutes: int = 60,
    ) -> list[str]:
        schedule = await self.get_schedule(barber_id)
        if not schedule:
            return []

        off_days = {
            int(item.strip())
            for item in (schedule["off_days"] or "").split(",")
            if item.strip().isdigit()
        }
        if target_date.weekday() in off_days:
            return []

        work_start = time.fromisoformat(schedule["work_start"])
        work_end = time.fromisoformat(schedule["work_end"])
        break_start = time.fromisoformat(schedule["break_start"]) if schedule["break_start"] else None
        break_end = time.fromisoformat(schedule["break_end"]) if schedule["break_end"] else None

        existing = await self._fetch_all(
            """
            SELECT b.booking_at, s.duration_minutes
            FROM bookings b
            JOIN services s ON s.id = b.service_id
            WHERE b.barber_id = ?
              AND b.status IN ('confirmed', 'completed')
              AND date(b.booking_at) = ?
            ORDER BY b.booking_at ASC
            """,
            (barber_id, target_date.isoformat()),
        )
        blocked_slots = set(await self.list_blocked_slots(barber_id, target_date))

        day_start = datetime.combine(target_date, work_start, tzinfo=self.timezone)
        closing_time = datetime.combine(target_date, work_end, tzinfo=self.timezone)
        break_window = None
        if break_start and break_end:
            break_window = (
                datetime.combine(target_date, break_start, tzinfo=self.timezone),
                datetime.combine(target_date, break_end, tzinfo=self.timezone),
            )

        slot_step = BUSINESS_HOURS["slot_step_minutes"]
        now = now_local(self.timezone)
        existing_windows: list[tuple[datetime, datetime]] = []
        for row in existing:
            booked_at = datetime.fromisoformat(row["booking_at"])
            booked_end = booked_at + timedelta(minutes=row["duration_minutes"])
            existing_windows.append((booked_at, booked_end))

        results: list[str] = []
        cursor = day_start
        duration = timedelta(minutes=service_duration_minutes)
        while cursor + duration <= closing_time:
            candidate_end = cursor + duration
            if cursor > now:
                overlaps = any(
                    cursor < existing_end and existing_start < candidate_end
                    for existing_start, existing_end in existing_windows
                )
                in_break = bool(
                    break_window and cursor < break_window[1] and break_window[0] < candidate_end
                )
                if not overlaps and not in_break and cursor.strftime("%H:%M") not in blocked_slots:
                    results.append(cursor.strftime("%H:%M"))
            cursor += timedelta(minutes=slot_step)
        return results

    async def create_booking(
        self,
        telegram_id: int,
        service_id: int,
        barber_id: int,
        booking_at: datetime,
        total_price: int,
    ) -> int:
        timestamp = now_local(self.timezone).isoformat()
        bonus_points = max(5, round(total_price * 0.05 / 1000))

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            user = await cursor.fetchone()
            if not user:
                raise RuntimeError("User must be registered before booking.")

            cursor = await db.execute(
                """
                INSERT INTO bookings (
                    user_id, service_id, barber_id, booking_at, total_price,
                    bonus_points_awarded, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user["id"],
                    service_id,
                    barber_id,
                    booking_at.isoformat(),
                    total_price,
                    bonus_points,
                    timestamp,
                    timestamp,
                ),
            )
            booking_id = int(cursor.lastrowid)
            await db.execute(
                """
                INSERT INTO bonus_transactions (user_id, booking_id, points_delta, reason, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user["id"], booking_id, bonus_points, "booking_reward", timestamp),
            )
            await db.execute(
                """
                UPDATE users
                SET loyalty_points = loyalty_points + ?, updated_at = ?
                WHERE id = ?
                """,
                (bonus_points, timestamp, user["id"]),
            )
            await db.commit()
        return booking_id

    async def get_booking_details(self, booking_id: int) -> dict[str, Any] | None:
        return await self._fetch_one(
            """
            SELECT
                b.id,
                b.booking_at,
                b.status,
                b.total_price,
                b.bonus_points_awarded,
                s.name AS service_name,
                s.duration_minutes,
                br.name AS barber_name
            FROM bookings b
            JOIN services s ON s.id = b.service_id
            JOIN barbers br ON br.id = b.barber_id
            WHERE b.id = ?
            """,
            (booking_id,),
        )

    async def get_admin_booking(self, booking_id: int) -> dict[str, Any] | None:
        return await self._fetch_one(
            """
            SELECT
                b.id,
                b.booking_at,
                b.status,
                b.total_price,
                u.full_name,
                COALESCE(u.phone, 'Telefon kiritilmagan') AS phone,
                s.name AS service_name,
                s.duration_minutes,
                br.id AS barber_id,
                br.name AS barber_name
            FROM bookings b
            JOIN users u ON u.id = b.user_id
            JOIN services s ON s.id = b.service_id
            JOIN barbers br ON br.id = b.barber_id
            WHERE b.id = ?
            """,
            (booking_id,),
        )

    async def list_today_bookings(self, day: date) -> list[dict[str, Any]]:
        return await self._fetch_all(
            """
            SELECT
                b.id,
                b.booking_at,
                b.total_price,
                b.status,
                u.full_name,
                COALESCE(u.phone, 'Telefon kiritilmagan') AS phone,
                s.name AS service_name,
                br.name AS barber_name
            FROM bookings b
            JOIN users u ON u.id = b.user_id
            JOIN services s ON s.id = b.service_id
            JOIN barbers br ON br.id = b.barber_id
            WHERE date(b.booking_at) = ?
            ORDER BY b.booking_at ASC
            """,
            (day.isoformat(),),
        )

    async def cancel_booking(self, booking_id: int, telegram_id: int) -> bool:
        timestamp = now_local(self.timezone).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT b.id, b.user_id, b.status, b.bonus_points_awarded, b.booking_at
                FROM bookings b
                JOIN users u ON u.id = b.user_id
                WHERE b.id = ? AND u.telegram_id = ?
                """,
                (booking_id, telegram_id),
            )
            booking = await cursor.fetchone()
            if not booking or booking["status"] != "confirmed":
                return False
            if datetime.fromisoformat(booking["booking_at"]) <= now_local(self.timezone):
                return False

            await db.execute(
                """
                UPDATE bookings
                SET status = 'cancelled', cancel_reason = 'user_cancelled', updated_at = ?
                WHERE id = ?
                """,
                (timestamp, booking_id),
            )
            if booking["bonus_points_awarded"] > 0:
                await db.execute(
                    """
                    INSERT INTO bonus_transactions (user_id, booking_id, points_delta, reason, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        booking["user_id"],
                        booking_id,
                        -booking["bonus_points_awarded"],
                        "booking_cancelled",
                        timestamp,
                    ),
                )
                await db.execute(
                    """
                    UPDATE users
                    SET loyalty_points = CASE
                        WHEN loyalty_points >= ? THEN loyalty_points - ?
                        ELSE 0
                    END,
                    updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        booking["bonus_points_awarded"],
                        booking["bonus_points_awarded"],
                        timestamp,
                        booking["user_id"],
                    ),
                )
            await db.commit()
        return True

    async def admin_cancel_booking(self, booking_id: int) -> bool:
        booking = await self.get_admin_booking(booking_id)
        if not booking or booking["status"] == "cancelled":
            return False
        await self._execute(
            """
            UPDATE bookings
            SET status = 'cancelled', cancel_reason = 'admin_cancelled', updated_at = ?
            WHERE id = ?
            """,
            (now_local(self.timezone).isoformat(), booking_id),
        )
        return True

    async def complete_booking(self, booking_id: int) -> bool:
        booking = await self.get_admin_booking(booking_id)
        if not booking or booking["status"] == "completed":
            return False
        timestamp = now_local(self.timezone).isoformat()
        await self._execute(
            """
            UPDATE bookings
            SET status = 'completed', completed_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (timestamp, timestamp, booking_id),
        )
        return True

    async def reschedule_booking(self, booking_id: int, new_booking_at: datetime) -> bool:
        booking = await self.get_admin_booking(booking_id)
        if not booking or booking["status"] == "cancelled":
            return False
        await self._execute(
            """
            UPDATE bookings
            SET booking_at = ?, status = 'confirmed', updated_at = ?
            WHERE id = ?
            """,
            (new_booking_at.isoformat(), now_local(self.timezone).isoformat(), booking_id),
        )
        return True

    async def get_bonus_summary(self, telegram_id: int) -> dict[str, Any] | None:
        return await self._fetch_one(
            """
            SELECT
                u.loyalty_points,
                COUNT(b.id) AS total_bookings,
                COALESCE(SUM(CASE WHEN b.status IN ('confirmed', 'completed') THEN b.total_price ELSE 0 END), 0) AS total_spent
            FROM users u
            LEFT JOIN bookings b ON b.user_id = u.id
            WHERE u.telegram_id = ?
            GROUP BY u.id
            """,
            (telegram_id,),
        )

    async def create_review(self, telegram_id: int, rating: int, comment: str) -> None:
        timestamp = now_local(self.timezone).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            user = await cursor.fetchone()
            if not user:
                return
            await db.execute(
                """
                INSERT INTO reviews (user_id, rating, comment, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user["id"], rating, comment, timestamp),
            )
            await db.commit()

    async def list_hairstyle_catalog(self) -> list[dict[str, Any]]:
        return await self._fetch_all(
            """
            SELECT
                slug,
                name,
                summary,
                face_shapes,
                hair_lengths,
                style_goals,
                maintenance_level,
                beard_styles,
                booking_service_name,
                reference_url
            FROM hairstyle_catalog
            WHERE is_active = 1
            ORDER BY sort_order ASC, name ASC
            """
        )

    async def create_style_consultation(
        self,
        telegram_id: int,
        photo_file_id: str,
        face_shape: str,
        hair_length: str,
        style_goal: str,
        maintenance_level: str,
        beard_style: str,
        recommendations: list[dict[str, Any]],
    ) -> None:
        timestamp = now_local(self.timezone).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            user = await cursor.fetchone()
            if not user:
                return
            await db.execute(
                """
                INSERT INTO style_consultations (
                    user_id, photo_file_id, face_shape, hair_length, style_goal,
                    maintenance_level, beard_style, recommendations_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user["id"],
                    photo_file_id,
                    face_shape,
                    hair_length,
                    style_goal,
                    maintenance_level,
                    beard_style,
                    json.dumps(recommendations, ensure_ascii=False),
                    timestamp,
                ),
            )
            await db.commit()

    async def get_dashboard_stats(self, today: date) -> dict[str, int]:
        today_row = await self._fetch_one(
            """
            SELECT
                COUNT(*) AS bookings_count,
                COALESCE(SUM(CASE WHEN status IN ('confirmed', 'completed') THEN total_price ELSE 0 END), 0) AS revenue,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled_count
            FROM bookings
            WHERE date(booking_at) = ?
            """,
            (today.isoformat(),),
        ) or {"bookings_count": 0, "revenue": 0, "cancelled_count": 0}
        week_row = await self._fetch_one(
            """
            SELECT COALESCE(SUM(total_price), 0) AS revenue
            FROM bookings
            WHERE date(booking_at) BETWEEN ? AND ?
              AND status IN ('confirmed', 'completed')
            """,
            (start_of_week(today).isoformat(), today.isoformat()),
        ) or {"revenue": 0}
        new_customers_row = await self._fetch_one(
            """
            SELECT COUNT(*) AS new_customers
            FROM users
            WHERE date(created_at) = ?
            """,
            (today.isoformat(),),
        ) or {"new_customers": 0}
        return {
            "today_bookings": int(today_row["bookings_count"] or 0),
            "today_revenue": int(today_row["revenue"] or 0),
            "weekly_revenue": int(week_row["revenue"] or 0),
            "new_customers": int(new_customers_row["new_customers"] or 0),
            "cancelled_bookings": int(today_row["cancelled_count"] or 0),
        }

    async def get_today_revenue(self, day: date) -> int:
        row = await self._fetch_one(
            """
            SELECT COALESCE(SUM(total_price), 0) AS revenue
            FROM bookings
            WHERE date(booking_at) = ?
              AND status IN ('confirmed', 'completed')
            """,
            (day.isoformat(),),
        )
        return int(row["revenue"]) if row else 0

    async def get_revenue_stats(self, today: date) -> dict[str, int]:
        day_row = await self._fetch_one(
            """
            SELECT COALESCE(SUM(total_price), 0) AS total
            FROM bookings
            WHERE date(booking_at) = ?
              AND status IN ('confirmed', 'completed')
            """,
            (today.isoformat(),),
        ) or {"total": 0}
        week_row = await self._fetch_one(
            """
            SELECT COALESCE(SUM(total_price), 0) AS total
            FROM bookings
            WHERE date(booking_at) BETWEEN ? AND ?
              AND status IN ('confirmed', 'completed')
            """,
            (start_of_week(today).isoformat(), today.isoformat()),
        ) or {"total": 0}
        month_row = await self._fetch_one(
            """
            SELECT COALESCE(SUM(total_price), 0) AS total
            FROM bookings
            WHERE date(booking_at) BETWEEN ? AND ?
              AND status IN ('confirmed', 'completed')
            """,
            (start_of_month(today).isoformat(), today.isoformat()),
        ) or {"total": 0}
        return {
            "daily": int(day_row["total"] or 0),
            "weekly": int(week_row["total"] or 0),
            "monthly": int(month_row["total"] or 0),
        }

    async def get_customer_stats(self) -> dict[str, Any]:
        return await self._fetch_one(
            """
            SELECT
                COUNT(*) AS total_customers,
                COUNT(CASE WHEN loyalty_points > 0 THEN 1 END) AS returning_customers
            FROM users
            """
        ) or {"total_customers": 0, "returning_customers": 0}

    async def create_barber_application(
        self,
        telegram_id: int,
        full_name: str,
        username: str | None,
        phone: str,
        specialty: str,
        experience_years: int,
        photo_file_id: str,
    ) -> None:
        timestamp = now_local(self.timezone).isoformat()
        await self._execute(
            """
            INSERT INTO barber_applications (
                telegram_id, full_name, username, phone, specialty, experience_years, photo_file_id,
                status, created_at, reviewed_at, approved_barber_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, NULL, NULL)
            ON CONFLICT(telegram_id) DO UPDATE SET
                full_name = excluded.full_name,
                username = excluded.username,
                phone = excluded.phone,
                specialty = excluded.specialty,
                experience_years = excluded.experience_years,
                photo_file_id = excluded.photo_file_id,
                status = 'pending',
                created_at = excluded.created_at,
                reviewed_at = NULL,
                approved_barber_id = NULL
            """,
            (telegram_id, full_name, username, phone, specialty, experience_years, photo_file_id, timestamp),
        )

    async def list_pending_barber_applications(self) -> list[dict[str, Any]]:
        return await self._fetch_all(
            """
            SELECT id, telegram_id, full_name, username, phone, specialty, experience_years, photo_file_id, created_at
            FROM barber_applications
            WHERE status = 'pending'
            ORDER BY created_at ASC
            """
        )

    async def approve_barber_application(self, application_id: int) -> dict[str, Any] | None:
        timestamp = now_local(self.timezone).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT id, telegram_id, full_name, username, phone, specialty, experience_years, photo_file_id, status
                FROM barber_applications
                WHERE id = ?
                """,
                (application_id,),
            )
            application = await cursor.fetchone()
            if not application or application["status"] != "pending":
                return None

            existing_cursor = await db.execute(
                "SELECT id FROM barbers WHERE telegram_id = ?",
                (application["telegram_id"],),
            )
            existing = await existing_cursor.fetchone()
            if existing:
                barber_id = int(existing["id"])
                await db.execute(
                    """
                    UPDATE barbers
                    SET name = ?, specialty = ?, experience_years = ?, username = ?, phone = ?, photo_file_id = ?, is_active = 1
                    WHERE id = ?
                    """,
                    (
                        application["full_name"],
                        application["specialty"],
                        application["experience_years"],
                        application["username"],
                        application["phone"],
                        application["photo_file_id"],
                        barber_id,
                    ),
                )
            else:
                insert_cursor = await db.execute(
                    """
                    INSERT INTO barbers (
                        name, specialty, experience_years, telegram_id, username, phone, bio, photo_file_id, is_active
                    )
                    VALUES (?, ?, ?, ?, ?, ?, NULL, ?, 1)
                    """,
                    (
                        application["full_name"],
                        application["specialty"],
                        application["experience_years"],
                        application["telegram_id"],
                        application["username"],
                        application["phone"],
                        application["photo_file_id"],
                    ),
                )
                barber_id = int(insert_cursor.lastrowid)
                await db.execute(
                    """
                    INSERT OR IGNORE INTO barber_schedules (
                        barber_id, work_start, work_end, break_start, break_end, off_days, updated_at
                    )
                    VALUES (?, '09:00', '21:00', NULL, NULL, '', ?)
                    """,
                    (barber_id, timestamp),
                )

            await db.execute(
                """
                UPDATE barber_applications
                SET status = 'approved', reviewed_at = ?, approved_barber_id = ?
                WHERE id = ?
                """,
                (timestamp, barber_id, application_id),
            )
            await db.commit()

        return await self.get_barber(barber_id)

    async def list_customers(self, limit: int = 20) -> list[dict[str, Any]]:
        return await self._fetch_all(
            """
            SELECT
                u.id,
                u.full_name,
                COALESCE(u.phone, 'Telefon kiritilmagan') AS phone,
                COUNT(CASE WHEN b.status IN ('confirmed', 'completed') THEN 1 END) AS visit_count,
                MAX(b.booking_at) AS last_visit_date,
                (
                    SELECT s2.name
                    FROM bookings b2
                    JOIN services s2 ON s2.id = b2.service_id
                    WHERE b2.user_id = u.id
                    ORDER BY b2.booking_at DESC
                    LIMIT 1
                ) AS last_haircut
            FROM users u
            LEFT JOIN bookings b ON b.user_id = u.id
            GROUP BY u.id
            ORDER BY MAX(u.updated_at) DESC
            LIMIT ?
            """,
            (limit,),
        )

    async def get_barber_dashboard_stats(self, barber_id: int, day: date) -> dict[str, int]:
        row = await self._fetch_one(
            """
            SELECT
                COUNT(*) AS total_bookings,
                COALESCE(SUM(CASE WHEN status IN ('confirmed', 'completed') THEN total_price ELSE 0 END), 0) AS revenue,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled_count
            FROM bookings
            WHERE barber_id = ? AND date(booking_at) = ?
            """,
            (barber_id, day.isoformat()),
        ) or {"total_bookings": 0, "revenue": 0, "cancelled_count": 0}
        return {
            "total_bookings": int(row["total_bookings"] or 0),
            "revenue": int(row["revenue"] or 0),
            "cancelled_count": int(row["cancelled_count"] or 0),
        }

    async def list_barber_bookings(self, barber_id: int, *, upcoming_only: bool = False, limit: int = 20) -> list[dict[str, Any]]:
        now_iso = now_local(self.timezone).isoformat()
        query = """
            SELECT
                b.id,
                b.booking_at,
                b.status,
                b.total_price,
                u.full_name,
                COALESCE(u.phone, 'Telefon kiritilmagan') AS phone,
                s.name AS service_name
            FROM bookings b
            JOIN users u ON u.id = b.user_id
            JOIN services s ON s.id = b.service_id
            WHERE b.barber_id = ?
        """
        params: list[Any] = [barber_id]
        if upcoming_only:
            query += " AND b.booking_at >= ? AND b.status IN ('confirmed', 'completed')"
            params.append(now_iso)
        else:
            query += " AND date(b.booking_at) = date(?)"
            params.append(now_local(self.timezone).date().isoformat())
        query += " ORDER BY b.booking_at ASC LIMIT ?"
        params.append(limit)
        return await self._fetch_all(query, tuple(params))

    async def list_cancelled_bookings(self, day: date) -> list[dict[str, Any]]:
        return await self._fetch_all(
            """
            SELECT
                b.id,
                b.booking_at,
                u.full_name,
                s.name AS service_name,
                br.name AS barber_name
            FROM bookings b
            JOIN users u ON u.id = b.user_id
            JOIN services s ON s.id = b.service_id
            JOIN barbers br ON br.id = b.barber_id
            WHERE date(b.booking_at) = ?
              AND b.status = 'cancelled'
            ORDER BY b.booking_at ASC
            """,
            (day.isoformat(),),
        )

    async def list_reviews(self, limit: int = 10) -> list[dict[str, Any]]:
        return await self._fetch_all(
            """
            SELECT
                r.id,
                r.rating,
                COALESCE(r.comment, '') AS comment,
                r.created_at,
                u.full_name
            FROM reviews r
            JOIN users u ON u.id = r.user_id
            ORDER BY r.created_at DESC
            LIMIT ?
            """,
            (limit,),
        )

    async def get_reviews_summary(self) -> dict[str, Any]:
        row = await self._fetch_one(
            """
            SELECT COUNT(*) AS total_reviews, COALESCE(AVG(rating), 0) AS avg_rating
            FROM reviews
            """
        )
        if not row:
            return {"total_reviews": 0, "avg_rating": 0.0}
        return {"total_reviews": int(row["total_reviews"]), "avg_rating": float(row["avg_rating"])}

    async def list_due_customer_reminders(self, lower_bound: datetime, upper_bound: datetime) -> list[dict[str, Any]]:
        return await self._fetch_all(
            """
            SELECT
                b.id,
                b.booking_at,
                u.telegram_id,
                u.full_name,
                s.name AS service_name,
                br.name AS barber_name
            FROM bookings b
            JOIN users u ON u.id = b.user_id
            JOIN services s ON s.id = b.service_id
            JOIN barbers br ON br.id = b.barber_id
            WHERE b.status = 'confirmed'
              AND b.reminder_sent_at IS NULL
              AND b.booking_at >= ?
              AND b.booking_at <= ?
            ORDER BY b.booking_at ASC
            """,
            (lower_bound.isoformat(), upper_bound.isoformat()),
        )

    async def list_due_barber_reminders(self, lower_bound: datetime, upper_bound: datetime) -> list[dict[str, Any]]:
        return await self._fetch_all(
            """
            SELECT
                b.id,
                b.booking_at,
                br.telegram_id,
                br.name AS barber_name,
                u.full_name,
                COALESCE(u.phone, 'Telefon kiritilmagan') AS phone,
                s.name AS service_name
            FROM bookings b
            JOIN users u ON u.id = b.user_id
            JOIN services s ON s.id = b.service_id
            JOIN barbers br ON br.id = b.barber_id
            WHERE b.status = 'confirmed'
              AND br.telegram_id IS NOT NULL
              AND b.barber_reminder_sent_at IS NULL
              AND b.booking_at >= ?
              AND b.booking_at <= ?
            ORDER BY b.booking_at ASC
            """,
            (lower_bound.isoformat(), upper_bound.isoformat()),
        )

    async def mark_customer_reminder_sent(self, booking_id: int) -> None:
        timestamp = now_local(self.timezone).isoformat()
        await self._execute(
            "UPDATE bookings SET reminder_sent_at = ?, updated_at = ? WHERE id = ?",
            (timestamp, timestamp, booking_id),
        )

    async def mark_barber_reminder_sent(self, booking_id: int) -> None:
        timestamp = now_local(self.timezone).isoformat()
        await self._execute(
            "UPDATE bookings SET barber_reminder_sent_at = ?, updated_at = ? WHERE id = ?",
            (timestamp, timestamp, booking_id),
        )

    async def _execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(query, params)
            await db.commit()

    async def _fetch_one(self, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def _fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
