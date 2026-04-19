from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class DashboardMetrics:
    today_bookings: int
    pending_requests: int
    monthly_revenue: int
    average_rating: float
    unread_chats: int


@dataclass(slots=True)
class BookingCard:
    booking_id: int
    client_name: str
    service_name: str
    date_label: str
    time_label: str
    phone_number: str
    status: str


@dataclass(slots=True)
class ProfileView:
    full_name: str
    salon_name: str
    phone_number: str
    address: str
    experience: str
    about_me: str
    profile_image_file_id: str | None
    portfolio_images: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ServiceCard:
    service_id: int
    name: str
    description: str
    duration_minutes: int
    price: int
    is_active: bool


@dataclass(slots=True)
class ScheduleView:
    working_days: list[int]
    start_time: str
    end_time: str
    break_start: str | None
    break_end: str | None
    vacation_mode: bool
    unavailable_dates: list[str]
    custom_open_slots: list[str]
    custom_closed_slots: list[str]


@dataclass(slots=True)
class ReviewCard:
    review_id: int
    client_name: str
    rating: int
    comment: str
    is_verified: bool
    reply_text: str | None
    created_at_label: str


@dataclass(slots=True)
class ReviewSummary:
    average_rating: float
    total_reviews: int
    verified_reviews: int
    reviews: list[ReviewCard]


@dataclass(slots=True)
class AnalyticsView:
    today_bookings: int
    weekly_bookings: int
    monthly_bookings: int
    monthly_revenue: int
    total_customers: int
    average_rating: float
    repeat_customers: int


@dataclass(slots=True)
class ChatThreadCard:
    thread_id: int
    client_name: str
    preview: str
    unread_count: int
    booking_related: bool
    booking_reference: str | None

