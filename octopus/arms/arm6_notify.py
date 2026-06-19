"""Arm 6 — Notifications: desktop / Slack alerts for pending actions."""

from __future__ import annotations

import json
import subprocess
import sys

import httpx

from octopus.config import load_config


class Notifier:
    def __init__(self) -> None:
        self._cfg = load_config().notifications

    def send(self, title: str, message: str) -> None:
        if self._cfg.provider == "slack" and self._cfg.slack_webhook:
            self._slack(title, message)
        else:
            self._system(title, message)

    def _system(self, title: str, message: str) -> None:
        if sys.platform == "darwin":
            subprocess.run(
                ["osascript", "-e", f'display notification "{message}" with title "{title}"'],
                check=False,
            )
        elif sys.platform.startswith("linux"):
            subprocess.run(["notify-send", title, message], check=False)
        else:
            print(f"[Notification] {title}: {message}")

    def _slack(self, title: str, message: str) -> None:
        payload = {"text": f"*{title}*\n{message}"}
        httpx.post(self._cfg.slack_webhook, json=payload, timeout=5)
