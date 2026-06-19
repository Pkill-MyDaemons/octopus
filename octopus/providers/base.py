"""Abstract base interfaces for every provider category."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from octopus.models import CalendarSlot, EmailMessage


class EmailProvider(ABC):
    @abstractmethod
    def fetch_unread(self, max_results: int = 20) -> list[EmailMessage]:
        ...

    @abstractmethod
    def send(self, to: str, subject: str, body: str, thread_id: str | None = None) -> str:
        """Send an email; return the sent message ID."""
        ...

    @abstractmethod
    def mark_read(self, message_id: str) -> None:
        ...


class CalendarProvider(ABC):
    @abstractmethod
    def list_events(self, start: datetime, end: datetime) -> list[dict]:
        ...

    @abstractmethod
    def find_free_slots(
        self,
        date: datetime,
        duration_minutes: int,
        earliest: str = "09:00",
        latest: str = "18:00",
    ) -> list[CalendarSlot]:
        ...

    @abstractmethod
    def hold_slot(self, slot: CalendarSlot, title: str = "Tentative Hold") -> str:
        """Create a tentative event; return event ID."""
        ...

    @abstractmethod
    def confirm_event(self, event_id: str, title: str, attendees: list[str]) -> str:
        ...

    @abstractmethod
    def delete_event(self, event_id: str) -> None:
        ...


class TaskProvider(ABC):
    @abstractmethod
    def create_task(
        self,
        title: str,
        project: str,
        priority: str = "Normal",
        notes: str = "",
        due_on: str | None = None,
    ) -> str:
        """Create a task; return task ID."""
        ...

    @abstractmethod
    def update_task(self, task_id: str, **kwargs) -> None:
        ...
