from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def format_money(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + " so'm"


def now_local(timezone: ZoneInfo) -> datetime:
    return datetime.now(timezone)


def format_datetime_uz(value: datetime) -> str:
    return value.strftime("%d.%m.%Y %H:%M")


def format_date_uz(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def format_status_uz(status: str) -> str:
    labels = {
        "confirmed": "Tasdiqlangan",
        "completed": "Yakunlangan",
        "cancelled": "Bekor qilingan",
    }
    return labels.get(status, status)


def start_of_week(day: date) -> date:
    return day - timedelta(days=day.weekday())


def start_of_month(day: date) -> date:
    return day.replace(day=1)


def parse_hhmm(value: str) -> time:
    return datetime.strptime(value.strip(), "%H:%M").time()


def parse_time_range(value: str) -> tuple[str, str]:
    start_text, end_text = (part.strip() for part in value.split("-", maxsplit=1))
    start = parse_hhmm(start_text)
    end = parse_hhmm(end_text)
    if start >= end:
        raise ValueError("start must be earlier than end")
    return start.strftime("%H:%M"), end.strftime("%H:%M")


def weekday_name_uz(index: int) -> str:
    mapping = {
        0: "Dushanba",
        1: "Seshanba",
        2: "Chorshanba",
        3: "Payshanba",
        4: "Juma",
        5: "Shanba",
        6: "Yakshanba",
    }
    return mapping[index]
