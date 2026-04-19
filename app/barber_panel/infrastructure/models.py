from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.barber_panel.domain.enums import BookingStatus, ChatMessageDirection
from app.barber_panel.infrastructure.base import Base, TimestampMixin


class Barber(TimestampMixin, Base):
    __tablename__ = "bp_barbers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    salon_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(32), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    experience: Mapped[str] = mapped_column(String(120), nullable=False)
    about_me: Mapped[str] = mapped_column(Text, default="", nullable=False)
    profile_image_file_id: Mapped[str | None] = mapped_column(String(255))
    theme: Mapped[str] = mapped_column(String(32), default="premium_dark", nullable=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    services: Mapped[list["Service"]] = relationship(back_populates="barber", cascade="all, delete-orphan")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="barber", cascade="all, delete-orphan")
    reviews: Mapped[list["Review"]] = relationship(back_populates="barber", cascade="all, delete-orphan")
    schedule: Mapped["Schedule | None"] = relationship(
        back_populates="barber",
        cascade="all, delete-orphan",
        uselist=False,
    )
    portfolio_images: Mapped[list["PortfolioImage"]] = relationship(
        back_populates="barber",
        cascade="all, delete-orphan",
        order_by="PortfolioImage.sort_order.asc()",
    )
    chat_threads: Mapped[list["ChatThread"]] = relationship(
        back_populates="barber",
        cascade="all, delete-orphan",
    )


class PortfolioImage(TimestampMixin, Base):
    __tablename__ = "bp_portfolio_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    barber_id: Mapped[int] = mapped_column(ForeignKey("bp_barbers.id", ondelete="CASCADE"), nullable=False)
    telegram_file_id: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    barber: Mapped[Barber] = relationship(back_populates="portfolio_images")


class Service(TimestampMixin, Base):
    __tablename__ = "bp_services"
    __table_args__ = (UniqueConstraint("barber_id", "name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    barber_id: Mapped[int] = mapped_column(ForeignKey("bp_barbers.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    barber: Mapped[Barber] = relationship(back_populates="services")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="service")


class Booking(TimestampMixin, Base):
    __tablename__ = "bp_bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    barber_id: Mapped[int] = mapped_column(ForeignKey("bp_barbers.id", ondelete="CASCADE"), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("bp_services.id", ondelete="RESTRICT"), nullable=False)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    client_telegram_id: Mapped[int | None] = mapped_column(Integer)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(
            BookingStatus,
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        default=BookingStatus.PENDING,
        nullable=False,
    )
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    barber: Mapped[Barber] = relationship(back_populates="bookings")
    service: Mapped[Service] = relationship(back_populates="bookings")
    review: Mapped["Review | None"] = relationship(back_populates="booking", uselist=False)
    thread: Mapped["ChatThread | None"] = relationship(back_populates="booking", uselist=False)


class Review(TimestampMixin, Base):
    __tablename__ = "bp_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    barber_id: Mapped[int] = mapped_column(ForeignKey("bp_barbers.id", ondelete="CASCADE"), nullable=False)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bp_bookings.id", ondelete="SET NULL"))
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reply_text: Mapped[str | None] = mapped_column(Text)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    barber: Mapped[Barber] = relationship(back_populates="reviews")
    booking: Mapped[Booking | None] = relationship(back_populates="review")


class Schedule(TimestampMixin, Base):
    __tablename__ = "bp_schedules"

    barber_id: Mapped[int] = mapped_column(ForeignKey("bp_barbers.id", ondelete="CASCADE"), primary_key=True)
    working_days: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    break_start: Mapped[time | None] = mapped_column(Time)
    break_end: Mapped[time | None] = mapped_column(Time)
    unavailable_dates: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    custom_open_slots: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    custom_closed_slots: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    vacation_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    barber: Mapped[Barber] = relationship(back_populates="schedule")


class ChatThread(TimestampMixin, Base):
    __tablename__ = "bp_chat_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    barber_id: Mapped[int] = mapped_column(ForeignKey("bp_barbers.id", ondelete="CASCADE"), nullable=False)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bp_bookings.id", ondelete="SET NULL"))
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_telegram_id: Mapped[int | None] = mapped_column(Integer)
    last_message_preview: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    unread_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    booking_related: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    barber: Mapped[Barber] = relationship(back_populates="chat_threads")
    booking: Mapped[Booking | None] = relationship(back_populates="thread")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at.asc()",
    )


class ChatMessage(TimestampMixin, Base):
    __tablename__ = "bp_chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("bp_chat_threads.id", ondelete="CASCADE"), nullable=False)
    direction: Mapped[ChatMessageDirection] = mapped_column(
        Enum(
            ChatMessageDirection,
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    thread: Mapped[ChatThread] = relationship(back_populates="messages")
