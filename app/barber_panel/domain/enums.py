from __future__ import annotations

from enum import StrEnum


class BookingStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ChatMessageDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"

