from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PaymentIntent:
    booking_id: int
    amount: int
    provider: str
    status: str = "pending"
    reference: str | None = None


class PaymentService:
    """
    Placeholder abstraction for future Click/Payme integrations.
    """

    async def create_intent(self, booking_id: int, amount: int, provider: str) -> PaymentIntent:
        return PaymentIntent(booking_id=booking_id, amount=amount, provider=provider)
