from __future__ import annotations


class BarberPanelError(Exception):
    """Base exception for barber panel failures."""


class AccessDeniedError(BarberPanelError):
    """Raised when a user cannot access barber panel."""


class EntityNotFoundError(BarberPanelError):
    """Raised when a requested entity does not exist."""


class ValidationError(BarberPanelError):
    """Raised when the supplied payload is invalid."""

