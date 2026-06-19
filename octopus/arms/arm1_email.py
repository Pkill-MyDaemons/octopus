"""Arm 1 — Email Poller: watches for new email and triggers workflows."""

from __future__ import annotations

import time
from typing import Callable

from octopus.config import load_config
from octopus.models import EmailMessage
from octopus.providers import get_email_provider
from octopus.security.injection import InjectionGuard


class EmailPoller:
    def __init__(self) -> None:
        cfg = load_config()
        self._provider = get_email_provider(cfg.email.provider)
        self._guard = InjectionGuard()
        self._poll_interval = cfg.email.poll_interval_seconds

    def fetch_unread(self, max_results: int = 20) -> list[EmailMessage]:
        messages = self._provider.fetch_unread(max_results)
        safe = []
        for msg in messages:
            result = self._guard.check(msg.body)
            if not result.safe:
                # Log and skip injected content rather than crashing
                print(f"[Arm 1] Skipped email {msg.message_id}: {result.reason}")
                continue
            safe.append(msg)
        return safe

    def send_reply(self, to: str, subject: str, body: str, thread_id: str | None = None) -> str:
        return self._provider.send(to, subject, body, thread_id)

    def mark_read(self, message_id: str) -> None:
        self._provider.mark_read(message_id)

    def poll_loop(self, callback: Callable[[EmailMessage], None]) -> None:
        """Continuously poll for new email and invoke callback for each message."""
        print(f"[Arm 1] Email poller started (interval: {self._poll_interval}s)")
        while True:
            try:
                for msg in self.fetch_unread():
                    callback(msg)
            except Exception as exc:
                print(f"[Arm 1] Poll error: {exc}")
            time.sleep(self._poll_interval)
