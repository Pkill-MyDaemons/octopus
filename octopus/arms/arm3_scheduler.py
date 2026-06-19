"""Arm 3 — Slot Scheduler: books, holds, and manages calendar events."""

from __future__ import annotations

from octopus.config import load_config
from octopus.models import CalendarSlot
from octopus.providers import get_calendar_provider


class SlotScheduler:
    def __init__(self) -> None:
        self._provider = get_calendar_provider(load_config().calendar.provider)

    def hold_tentative(self, slot: CalendarSlot, title: str = "Tentative Hold") -> str:
        """Block a slot as tentative; returns the event ID for later confirmation."""
        return self._provider.hold_slot(slot, title)

    def confirm(self, event_id: str, title: str, attendees: list[str]) -> str:
        return self._provider.confirm_event(event_id, title, attendees)

    def release_hold(self, event_id: str) -> None:
        self._provider.delete_event(event_id)

    def hold_multiple(self, slots: list[CalendarSlot], title: str = "Tentative Hold") -> list[str]:
        return [self.hold_tentative(s, title) for s in slots]
