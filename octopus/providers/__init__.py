"""Provider registry — resolve provider implementations by name."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from octopus.providers.base import EmailProvider, CalendarProvider, TaskProvider


def get_email_provider(name: str) -> "EmailProvider":
    if name == "gmail":
        from octopus.providers.gmail import GmailProvider
        return GmailProvider()
    if name == "imap":
        from octopus.providers.imap import IMAPProvider
        return IMAPProvider()
    raise ValueError(f"Unknown email provider: {name!r}")


def get_calendar_provider(name: str) -> "CalendarProvider":
    if name == "google_calendar":
        from octopus.providers.google_calendar import GoogleCalendarProvider
        return GoogleCalendarProvider()
    raise ValueError(f"Unknown calendar provider: {name!r}")


def get_task_provider(name: str) -> "TaskProvider":
    if name == "asana":
        from octopus.providers.asana_provider import AsanaProvider
        return AsanaProvider()
    if name == "markdown":
        from octopus.providers.markdown_tasks import MarkdownTaskProvider
        return MarkdownTaskProvider()
    raise ValueError(f"Unknown task provider: {name!r}")
