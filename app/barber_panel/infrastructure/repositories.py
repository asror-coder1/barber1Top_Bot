from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.barber_panel.domain.enums import ChatMessageDirection
from app.barber_panel.domain.exceptions import EntityNotFoundError
from app.barber_panel.infrastructure.models import (
    Barber,
    Booking,
    ChatMessage,
    ChatThread,
    PortfolioImage,
    Review,
    Schedule,
    Service,
)


class BarberPanelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_barber_by_telegram_id(self, telegram_id: int) -> Barber | None:
        result = await self.session.execute(
            select(Barber)
            .where(Barber.telegram_id == telegram_id, Barber.is_active.is_(True))
            .options(
                selectinload(Barber.services),
                selectinload(Barber.portfolio_images),
                selectinload(Barber.schedule),
            )
        )
        return result.scalar_one_or_none()

    async def create_default_schedule(self, barber_id: int) -> Schedule:
        schedule = Schedule(
            barber_id=barber_id,
            working_days=[0, 1, 2, 3, 4, 5],
            start_time=time(hour=10),
            end_time=time(hour=21),
            unavailable_dates=[],
            custom_open_slots=[],
            custom_closed_slots=[],
        )
        self.session.add(schedule)
        await self.session.flush()
        return schedule

    async def list_bookings_for_today(self, barber_id: int, target_day: date) -> list[Booking]:
        start = datetime.combine(target_day, time.min)
        end = datetime.combine(target_day, time.max)
        result = await self.session.execute(
            select(Booking)
            .where(
                Booking.barber_id == barber_id,
                Booking.scheduled_at >= start,
                Booking.scheduled_at <= end,
            )
            .options(joinedload(Booking.service))
            .order_by(Booking.scheduled_at.asc())
        )
        return list(result.scalars().unique().all())

    async def list_upcoming_bookings(self, barber_id: int, now_value: datetime) -> list[Booking]:
        result = await self.session.execute(
            select(Booking)
            .where(Booking.barber_id == barber_id, Booking.scheduled_at >= now_value)
            .options(joinedload(Booking.service))
            .order_by(Booking.scheduled_at.asc())
        )
        return list(result.scalars().unique().all())

    async def list_bookings_by_status(self, barber_id: int, status: str) -> list[Booking]:
        result = await self.session.execute(
            select(Booking)
            .where(Booking.barber_id == barber_id, Booking.status == status)
            .options(joinedload(Booking.service))
            .order_by(Booking.scheduled_at.asc())
        )
        return list(result.scalars().unique().all())

    async def get_booking(self, barber_id: int, booking_id: int) -> Booking | None:
        result = await self.session.execute(
            select(Booking)
            .where(Booking.barber_id == barber_id, Booking.id == booking_id)
            .options(joinedload(Booking.service))
        )
        return result.scalar_one_or_none()

    async def list_services(self, barber_id: int, include_inactive: bool = True) -> list[Service]:
        statement = select(Service).where(Service.barber_id == barber_id).order_by(Service.price.asc(), Service.name.asc())
        if not include_inactive:
            statement = statement.where(Service.is_active.is_(True))
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_service(self, barber_id: int, service_id: int) -> Service | None:
        result = await self.session.execute(
            select(Service).where(Service.barber_id == barber_id, Service.id == service_id)
        )
        return result.scalar_one_or_none()

    async def list_reviews(self, barber_id: int, limit: int = 10) -> list[Review]:
        result = await self.session.execute(
            select(Review)
            .where(Review.barber_id == barber_id)
            .order_by(Review.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_review(self, barber_id: int, review_id: int) -> Review | None:
        result = await self.session.execute(
            select(Review).where(Review.barber_id == barber_id, Review.id == review_id)
        )
        return result.scalar_one_or_none()

    async def list_chat_threads(self, barber_id: int, limit: int = 20) -> list[ChatThread]:
        result = await self.session.execute(
            select(ChatThread)
            .where(ChatThread.barber_id == barber_id)
            .order_by(ChatThread.updated_at.desc())
            .options(selectinload(ChatThread.messages), joinedload(ChatThread.booking))
            .limit(limit)
        )
        return list(result.scalars().unique().all())

    async def get_chat_thread(self, barber_id: int, thread_id: int) -> ChatThread | None:
        result = await self.session.execute(
            select(ChatThread)
            .where(ChatThread.barber_id == barber_id, ChatThread.id == thread_id)
            .options(selectinload(ChatThread.messages), joinedload(ChatThread.booking))
        )
        return result.scalar_one_or_none()

    async def unread_chat_count(self, barber_id: int) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.sum(ChatThread.unread_count), 0)).where(ChatThread.barber_id == barber_id)
        )
        return int(result.scalar_one() or 0)

    async def create_outbound_chat_message(self, thread: ChatThread, body: str) -> ChatMessage:
        message = ChatMessage(
            thread_id=thread.id,
            direction=ChatMessageDirection.OUTBOUND,
            body=body,
            is_read=True,
        )
        self.session.add(message)
        thread.last_message_preview = body[:120]
        thread.unread_count = 0
        await self.session.flush()
        return message

    async def mark_thread_read(self, thread: ChatThread) -> None:
        thread.unread_count = 0
        for message in thread.messages:
            message.is_read = True
        await self.session.flush()

    async def add_portfolio_image(self, barber_id: int, file_id: str) -> PortfolioImage:
        count_result = await self.session.execute(
            select(func.count(PortfolioImage.id)).where(PortfolioImage.barber_id == barber_id)
        )
        image = PortfolioImage(
            barber_id=barber_id,
            telegram_file_id=file_id,
            sort_order=int(count_result.scalar_one() or 0) + 1,
        )
        self.session.add(image)
        await self.session.flush()
        return image

    async def reviews_summary(self, barber_id: int) -> dict[str, int | float]:
        result = await self.session.execute(
            select(
                func.count(Review.id),
                func.coalesce(func.avg(Review.rating), 0),
                func.count(case((Review.is_verified.is_(True), 1))),
            ).where(Review.barber_id == barber_id)
        )
        total_reviews, average_rating, verified_reviews = result.one()
        return {
            "total_reviews": int(total_reviews or 0),
            "average_rating": float(average_rating or 0),
            "verified_reviews": int(verified_reviews or 0),
        }

    async def dashboard_metrics(self, barber_id: int, now_value: datetime) -> dict[str, int | float]:
        month_start = now_value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        today_start = now_value.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        bookings_today = await self.session.execute(
            select(func.count(Booking.id)).where(
                Booking.barber_id == barber_id,
                Booking.scheduled_at >= today_start,
                Booking.scheduled_at < today_end,
            )
        )
        pending_requests = await self.session.execute(
            select(func.count(Booking.id)).where(Booking.barber_id == barber_id, Booking.status == "pending")
        )
        monthly_revenue = await self.session.execute(
            select(func.coalesce(func.sum(Service.price), 0))
            .select_from(Booking)
            .join(Service, Service.id == Booking.service_id)
            .where(
                Booking.barber_id == barber_id,
                Booking.status.in_(("accepted", "completed")),
                Booking.scheduled_at >= month_start,
            )
        )
        average_rating = await self.session.execute(
            select(func.coalesce(func.avg(Review.rating), 0)).where(Review.barber_id == barber_id)
        )
        return {
            "today_bookings": int(bookings_today.scalar_one() or 0),
            "pending_requests": int(pending_requests.scalar_one() or 0),
            "monthly_revenue": int(monthly_revenue.scalar_one() or 0),
            "average_rating": float(average_rating.scalar_one() or 0),
        }

    async def analytics(self, barber_id: int, now_value: datetime) -> dict[str, int | float]:
        today_start = now_value.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)

        def count_from(start_at: datetime):
            return select(func.count(Booking.id)).where(
                Booking.barber_id == barber_id,
                Booking.scheduled_at >= start_at,
            )

        today_bookings = await self.session.execute(count_from(today_start))
        weekly_bookings = await self.session.execute(count_from(week_start))
        monthly_bookings = await self.session.execute(count_from(month_start))
        monthly_revenue = await self.session.execute(
            select(func.coalesce(func.sum(Service.price), 0))
            .select_from(Booking)
            .join(Service, Service.id == Booking.service_id)
            .where(
                Booking.barber_id == barber_id,
                Booking.status.in_(("accepted", "completed")),
                Booking.scheduled_at >= month_start,
            )
        )
        total_customers = await self.session.execute(
            select(func.count(func.distinct(Booking.client_phone))).where(Booking.barber_id == barber_id)
        )
        repeat_customers = await self.session.execute(
            select(func.count())
            .select_from(
                select(Booking.client_phone)
                .where(Booking.barber_id == barber_id)
                .group_by(Booking.client_phone)
                .having(func.count(Booking.id) > 1)
                .subquery()
            )
        )
        average_rating = await self.session.execute(
            select(func.coalesce(func.avg(Review.rating), 0)).where(Review.barber_id == barber_id)
        )
        return {
            "today_bookings": int(today_bookings.scalar_one() or 0),
            "weekly_bookings": int(weekly_bookings.scalar_one() or 0),
            "monthly_bookings": int(monthly_bookings.scalar_one() or 0),
            "monthly_revenue": int(monthly_revenue.scalar_one() or 0),
            "total_customers": int(total_customers.scalar_one() or 0),
            "average_rating": float(average_rating.scalar_one() or 0),
            "repeat_customers": int(repeat_customers.scalar_one() or 0),
        }


async def require_entity[T](entity: T | None, entity_name: str) -> T:
    if entity is None:
        raise EntityNotFoundError(f"{entity_name} not found")
    return entity
