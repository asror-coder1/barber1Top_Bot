from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.barber_panel.application.dtos import (
    AnalyticsView,
    BookingCard,
    ChatThreadCard,
    DashboardMetrics,
    ProfileView,
    ReviewCard,
    ReviewSummary,
    ScheduleView,
    ServiceCard,
)
from app.barber_panel.domain.exceptions import AccessDeniedError, ValidationError
from app.barber_panel.infrastructure.models import Schedule, Service
from app.barber_panel.infrastructure.repositories import BarberPanelRepository, require_entity

logger = logging.getLogger(__name__)

MONTHS_UZ = {
    1: "yanvar",
    2: "fevral",
    3: "mart",
    4: "aprel",
    5: "may",
    6: "iyun",
    7: "iyul",
    8: "avgust",
    9: "sentyabr",
    10: "oktyabr",
    11: "noyabr",
    12: "dekabr",
}


class BarberPanelService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        redis: Redis | None,
        timezone_now,
        allowed_ids: set[int] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._redis = redis
        self._timezone_now = timezone_now
        self._allowed_ids = allowed_ids or set()

    @asynccontextmanager
    async def _uow(self) -> AsyncSession:
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def get_barber_or_raise(self, telegram_id: int):
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await repo.get_barber_by_telegram_id(telegram_id)
            if barber:
                if not barber.schedule:
                    await repo.create_default_schedule(barber.id)
                    await session.refresh(barber)
                return barber
            if telegram_id in self._allowed_ids:
                raise AccessDeniedError("Barber panel profilini avval bazaga qo'shing.")
            raise AccessDeniedError("Siz barber panel foydalanuvchisi emassiz.")

    async def has_access(self, telegram_id: int) -> bool:
        try:
            await self.get_barber_or_raise(telegram_id)
        except AccessDeniedError:
            return False
        return True

    async def get_dashboard(self, telegram_id: int) -> DashboardMetrics:
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            metrics = await repo.dashboard_metrics(barber.id, self._timezone_now())
            unread = await self._get_unread_count(repo, barber.id)
            return DashboardMetrics(
                today_bookings=int(metrics["today_bookings"]),
                pending_requests=int(metrics["pending_requests"]),
                monthly_revenue=int(metrics["monthly_revenue"]),
                average_rating=float(metrics["average_rating"]),
                unread_chats=unread,
            )

    async def list_bookings(self, telegram_id: int, filter_key: str) -> list[BookingCard]:
        now_value = self._timezone_now()
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            if filter_key == "today":
                bookings = await repo.list_bookings_for_today(barber.id, now_value.date())
            elif filter_key == "upcoming":
                bookings = await repo.list_upcoming_bookings(barber.id, now_value)
            else:
                bookings = await repo.list_bookings_by_status(barber.id, filter_key)
            return [self._to_booking_card(item) for item in bookings]

    async def update_booking_status(self, telegram_id: int, booking_id: int, action: str) -> BookingCard:
        status_map = {"accept": "accepted", "reject": "cancelled", "complete": "completed"}
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            booking = await require_entity(await repo.get_booking(barber.id, booking_id), "booking")
            booking.status = status_map[action]
            await session.flush()
            logger.info("Booking %s updated by barber %s: %s", booking_id, barber.id, action)
            return self._to_booking_card(booking)

    async def reschedule_booking(self, telegram_id: int, booking_id: int, new_datetime: datetime) -> BookingCard:
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            booking = await require_entity(await repo.get_booking(barber.id, booking_id), "booking")
            booking.scheduled_at = new_datetime
            booking.status = "accepted"
            await session.flush()
            return self._to_booking_card(booking)

    async def get_profile(self, telegram_id: int) -> ProfileView:
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            return self._to_profile_view(barber)

    async def update_profile_field(self, telegram_id: int, field_name: str, value: str) -> ProfileView:
        field_map = {
            "full_name": "full_name",
            "salon_name": "salon_name",
            "phone": "phone_number",
            "address": "address",
            "experience": "experience",
            "about": "about_me",
        }
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            setattr(barber, field_map[field_name], value.strip())
            await session.flush()
            return self._to_profile_view(barber)

    async def update_profile_photo(self, telegram_id: int, file_id: str) -> ProfileView:
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            barber.profile_image_file_id = file_id
            await session.flush()
            refreshed = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            return self._to_profile_view(refreshed)

    async def add_portfolio_image(self, telegram_id: int, file_id: str) -> ProfileView:
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            await repo.add_portfolio_image(barber.id, file_id)
            await session.flush()
            refreshed = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            return self._to_profile_view(refreshed)

    async def list_services(self, telegram_id: int) -> list[ServiceCard]:
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            services = await repo.list_services(barber.id, include_inactive=True)
            return [self._to_service_card(item) for item in services]

    async def create_service(
        self,
        telegram_id: int,
        *,
        name: str,
        description: str,
        duration_minutes: int,
        price: int,
    ) -> list[ServiceCard]:
        self._validate_service(duration_minutes, price)
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            session.add(
                Service(
                    barber_id=barber.id,
                    name=name.strip(),
                    description=description.strip(),
                    duration_minutes=duration_minutes,
                    price=price,
                )
            )
            await session.flush()
            services = await repo.list_services(barber.id, include_inactive=True)
            return [self._to_service_card(item) for item in services]

    async def update_service(self, telegram_id: int, service_id: int, *, field_name: str, value: str) -> list[ServiceCard]:
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            service = await require_entity(await repo.get_service(barber.id, service_id), "service")
            if field_name == "price":
                self._validate_service(service.duration_minutes, int(value))
                service.price = int(value)
            elif field_name == "duration":
                self._validate_service(int(value), service.price)
                service.duration_minutes = int(value)
            elif field_name == "name":
                service.name = value.strip()
            elif field_name == "description":
                service.description = value.strip()
            await session.flush()
            services = await repo.list_services(barber.id, include_inactive=True)
            return [self._to_service_card(item) for item in services]

    async def bulk_update_prices(self, telegram_id: int, percent_delta: int) -> list[ServiceCard]:
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            services = await repo.list_services(barber.id, include_inactive=True)
            for service in services:
                service.price = max(1000, int(service.price * (100 + percent_delta) / 100))
            await session.flush()
            return [self._to_service_card(item) for item in services]

    async def delete_service(self, telegram_id: int, service_id: int) -> list[ServiceCard]:
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            service = await require_entity(await repo.get_service(barber.id, service_id), "service")
            service.is_active = False
            await session.flush()
            services = await repo.list_services(barber.id, include_inactive=True)
            return [self._to_service_card(item) for item in services]

    async def get_schedule(self, telegram_id: int) -> ScheduleView:
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            schedule = barber.schedule or await repo.create_default_schedule(barber.id)
            await session.flush()
            return self._to_schedule_view(schedule)

    async def toggle_working_day(self, telegram_id: int, weekday_index: int) -> ScheduleView:
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            schedule = barber.schedule or await repo.create_default_schedule(barber.id)
            working_days = set(schedule.working_days)
            if weekday_index in working_days:
                working_days.remove(weekday_index)
            else:
                working_days.add(weekday_index)
            schedule.working_days = sorted(working_days)
            await session.flush()
            return self._to_schedule_view(schedule)

    async def update_schedule_hours(self, telegram_id: int, start_at: str, end_at: str) -> ScheduleView:
        start_time = time.fromisoformat(start_at)
        end_time = time.fromisoformat(end_at)
        if start_time >= end_time:
            raise ValidationError("Boshlanish tugashdan oldin bo'lishi kerak.")
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            schedule = barber.schedule or await repo.create_default_schedule(barber.id)
            schedule.start_time = start_time
            schedule.end_time = end_time
            await session.flush()
            return self._to_schedule_view(schedule)

    async def update_schedule_break(self, telegram_id: int, start_at: str | None, end_at: str | None) -> ScheduleView:
        break_start = time.fromisoformat(start_at) if start_at else None
        break_end = time.fromisoformat(end_at) if end_at else None
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            schedule = barber.schedule or await repo.create_default_schedule(barber.id)
            schedule.break_start = break_start
            schedule.break_end = break_end
            await session.flush()
            return self._to_schedule_view(schedule)

    async def add_unavailable_date(self, telegram_id: int, raw_date: str) -> ScheduleView:
        date.fromisoformat(raw_date)
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            schedule = barber.schedule or await repo.create_default_schedule(barber.id)
            values = set(schedule.unavailable_dates)
            values.add(raw_date)
            schedule.unavailable_dates = sorted(values)
            await session.flush()
            return self._to_schedule_view(schedule)

    async def toggle_vacation_mode(self, telegram_id: int) -> ScheduleView:
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            schedule = barber.schedule or await repo.create_default_schedule(barber.id)
            schedule.vacation_mode = not schedule.vacation_mode
            await session.flush()
            return self._to_schedule_view(schedule)

    async def add_custom_slot(self, telegram_id: int, slot_type: str, raw_slot: str) -> ScheduleView:
        datetime.fromisoformat(raw_slot)
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            schedule = barber.schedule or await repo.create_default_schedule(barber.id)
            if slot_type == "open":
                values = set(schedule.custom_open_slots)
                values.add(raw_slot)
                schedule.custom_open_slots = sorted(values)
            else:
                values = set(schedule.custom_closed_slots)
                values.add(raw_slot)
                schedule.custom_closed_slots = sorted(values)
            await session.flush()
            return self._to_schedule_view(schedule)

    async def get_reviews(self, telegram_id: int) -> ReviewSummary:
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            summary = await repo.reviews_summary(barber.id)
            reviews = await repo.list_reviews(barber.id)
            return self._to_review_summary(summary, reviews)

    async def reply_to_review(self, telegram_id: int, review_id: int, reply_text: str) -> ReviewSummary:
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            review = await require_entity(await repo.get_review(barber.id, review_id), "review")
            review.reply_text = reply_text.strip()
            review.replied_at = self._timezone_now()
            await session.flush()
            summary = await repo.reviews_summary(barber.id)
            reviews = await repo.list_reviews(barber.id)
            return self._to_review_summary(summary, reviews)

    async def get_analytics(self, telegram_id: int) -> AnalyticsView:
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            stats = await repo.analytics(barber.id, self._timezone_now())
            return AnalyticsView(
                today_bookings=int(stats["today_bookings"]),
                weekly_bookings=int(stats["weekly_bookings"]),
                monthly_bookings=int(stats["monthly_bookings"]),
                monthly_revenue=int(stats["monthly_revenue"]),
                total_customers=int(stats["total_customers"]),
                average_rating=float(stats["average_rating"]),
                repeat_customers=int(stats["repeat_customers"]),
            )

    async def get_chat_threads(self, telegram_id: int) -> list[ChatThreadCard]:
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            threads = await repo.list_chat_threads(barber.id)
            await self._set_unread_cache(barber.id, await repo.unread_chat_count(barber.id))
            return [
                ChatThreadCard(
                    thread_id=thread.id,
                    client_name=thread.client_name,
                    preview=thread.last_message_preview,
                    unread_count=thread.unread_count,
                    booking_related=thread.booking_related,
                    booking_reference=f"#{thread.booking.id}" if thread.booking else None,
                )
                for thread in threads
            ]

    async def toggle_notifications(self, telegram_id: int) -> bool:
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            barber.notifications_enabled = not barber.notifications_enabled
            await session.flush()
            return barber.notifications_enabled

    async def toggle_theme(self, telegram_id: int) -> str:
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            barber.theme = "premium_white" if barber.theme == "premium_dark" else "premium_dark"
            await session.flush()
            return barber.theme

    async def get_chat_thread_messages(self, telegram_id: int, thread_id: int) -> tuple[ChatThreadCard, list[str]]:
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            thread = await require_entity(await repo.get_chat_thread(barber.id, thread_id), "chat_thread")
            await repo.mark_thread_read(thread)
            await self._set_unread_cache(barber.id, await repo.unread_chat_count(barber.id))
            return (
                ChatThreadCard(
                    thread_id=thread.id,
                    client_name=thread.client_name,
                    preview=thread.last_message_preview,
                    unread_count=0,
                    booking_related=thread.booking_related,
                    booking_reference=f"#{thread.booking.id}" if thread.booking else None,
                ),
                [
                    f"{'Mijoz' if message.direction.value == 'inbound' else 'Siz'}: {message.body}"
                    for message in thread.messages[-10:]
                ],
            )

    async def send_quick_reply(self, telegram_id: int, thread_id: int, body: str) -> list[str]:
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            thread = await require_entity(await repo.get_chat_thread(barber.id, thread_id), "chat_thread")
            await repo.create_outbound_chat_message(thread, body.strip())
            await session.flush()
            return [
                f"{'Mijoz' if message.direction.value == 'inbound' else 'Siz'}: {message.body}"
                for message in thread.messages[-10:]
            ]

    async def get_available_reschedule_slots(self, telegram_id: int, target_date: date) -> dict[str, list[str]]:
        async with self._uow() as session:
            repo = BarberPanelRepository(session)
            barber = await require_entity(await repo.get_barber_by_telegram_id(telegram_id), "barber")
            schedule = barber.schedule or await repo.create_default_schedule(barber.id)
            slots = self._generate_slots(schedule, target_date)
            return {
                "morning": [slot for slot in slots if int(slot[:2]) < 15],
                "evening": [slot for slot in slots if int(slot[:2]) >= 15],
            }

    async def _get_unread_count(self, repo: BarberPanelRepository, barber_id: int) -> int:
        if self._redis is not None:
            cached = await self._redis.get(f"barber_panel:{barber_id}:unread_chats")
            if cached is not None:
                return int(cached)
        count = await repo.unread_chat_count(barber_id)
        await self._set_unread_cache(barber_id, count)
        return count

    async def _set_unread_cache(self, barber_id: int, count: int) -> None:
        if self._redis is not None:
            await self._redis.setex(f"barber_panel:{barber_id}:unread_chats", 300, str(count))

    def _validate_service(self, duration_minutes: int, price: int) -> None:
        if duration_minutes <= 0 or price <= 0:
            raise ValidationError("Davomiylik va narx musbat bo'lishi kerak.")

    def _to_booking_card(self, booking) -> BookingCard:
        status = booking.status.value if hasattr(booking.status, "value") else str(booking.status)
        return BookingCard(
            booking_id=booking.id,
            client_name=booking.client_name,
            service_name=booking.service.name,
            date_label=f"{booking.scheduled_at.day}-{MONTHS_UZ[booking.scheduled_at.month]}",
            time_label=booking.scheduled_at.strftime("%H:%M"),
            phone_number=booking.client_phone,
            status=status,
        )

    def _to_service_card(self, service: Service) -> ServiceCard:
        return ServiceCard(
            service_id=service.id,
            name=service.name,
            description=service.description,
            duration_minutes=service.duration_minutes,
            price=service.price,
            is_active=service.is_active,
        )

    def _to_profile_view(self, barber) -> ProfileView:
        return ProfileView(
            full_name=barber.full_name,
            salon_name=barber.salon_name,
            phone_number=barber.phone_number,
            address=barber.address,
            experience=barber.experience,
            about_me=barber.about_me,
            profile_image_file_id=barber.profile_image_file_id,
            portfolio_images=[image.telegram_file_id for image in barber.portfolio_images],
        )

    def _to_schedule_view(self, schedule: Schedule) -> ScheduleView:
        return ScheduleView(
            working_days=schedule.working_days,
            start_time=schedule.start_time.strftime("%H:%M"),
            end_time=schedule.end_time.strftime("%H:%M"),
            break_start=schedule.break_start.strftime("%H:%M") if schedule.break_start else None,
            break_end=schedule.break_end.strftime("%H:%M") if schedule.break_end else None,
            vacation_mode=schedule.vacation_mode,
            unavailable_dates=schedule.unavailable_dates,
            custom_open_slots=schedule.custom_open_slots,
            custom_closed_slots=schedule.custom_closed_slots,
        )

    def _to_review_card(self, review) -> ReviewCard:
        return ReviewCard(
            review_id=review.id,
            client_name=review.client_name,
            rating=review.rating,
            comment=review.comment,
            is_verified=review.is_verified,
            reply_text=review.reply_text,
            created_at_label=review.created_at.strftime("%d.%m %H:%M"),
        )

    def _to_review_summary(self, summary: dict[str, int | float], reviews: list) -> ReviewSummary:
        return ReviewSummary(
            average_rating=float(summary["average_rating"]),
            total_reviews=int(summary["total_reviews"]),
            verified_reviews=int(summary["verified_reviews"]),
            reviews=[self._to_review_card(item) for item in reviews],
        )

    def _generate_slots(self, schedule: Schedule, target_date: date) -> list[str]:
        if schedule.vacation_mode or target_date.isoformat() in schedule.unavailable_dates:
            return []
        if target_date.weekday() not in set(schedule.working_days):
            return []
        slots: list[str] = []
        cursor = datetime.combine(target_date, schedule.start_time)
        end_at = datetime.combine(target_date, schedule.end_time)
        break_start = datetime.combine(target_date, schedule.break_start) if schedule.break_start else None
        break_end = datetime.combine(target_date, schedule.break_end) if schedule.break_end else None
        while cursor < end_at:
            if break_start and break_end and break_start <= cursor < break_end:
                cursor = break_end
                continue
            slots.append(cursor.strftime("%H:%M"))
            cursor += timedelta(minutes=30)
        return slots
