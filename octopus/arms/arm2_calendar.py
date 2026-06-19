"""Arm 2 — Calendar Reader: reads calendar events and availability."""

from __future__ import annotations

from datetime import datetime, timedelta

from octopus.config import load_config
from octopus.models import CalendarSlot
from octopus.providers import get_calendar_provider


class CalendarReader:
    def __init__(self) -> None:
        cfg = load_config()
        self._provider = get_calendar_provider(cfg.calendar.provider)
        self._cfg = cfg.calendar

    def get_events(self, start: datetime, end: datetime) -> list[dict]:
        return self._provider.list_events(start, end)

    def get_today_events(self) -> list[dict]:
        now = datetime.utcnow()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return self._provider.list_events(start, end)

    def is_busy_at(self, when: datetime, duration_minutes: int = 30) -> bool:
        end = when + timedelta(minutes=duration_minutes)
        events = self._provider.list_events(when, end)
        return len(events) > 0

    def find_free_slots(
        self,
        date: datetime,
        duration_minutes: int | None = None,
    ) -> list[CalendarSlot]:
        duration = duration_minutes or self._cfg.slot_duration_minutes
        return self._provider.find_free_slots(
            date=date,
            duration_minutes=duration,
            earliest=self._cfg.no_meetings_before,
            latest=self._cfg.no_meetings_after,
        )
