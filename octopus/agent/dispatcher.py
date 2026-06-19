"""Trigger dispatcher — maps incoming events to the right workflow."""

from __future__ import annotations

from typing import Any

from octopus.models import EmailMessage
from octopus.workflows import WorkflowEngine, list_workflows, load_workflow


class Dispatcher:
    def __init__(self, brain=None) -> None:
        self._engine = WorkflowEngine(brain=brain)
        self._workflows = self._load_email_workflows()

    def _load_email_workflows(self) -> list[dict]:
        """Load all workflows that have an email_keyword trigger."""
        result = []
        for name in list_workflows():
            try:
                wf = load_workflow(name)
                trigger = wf.get("trigger", {})
                if trigger.get("type") == "email_keyword":
                    result.append({"name": name, "keywords": trigger.get("keywords", [])})
            except Exception:
                continue
        return result

    def dispatch_email(self, msg: EmailMessage) -> list[str]:
        """Match email against keyword triggers; run matching workflows."""
        text = (msg.subject + " " + msg.body).lower()
        run_ids = []
        for wf in self._workflows:
            if any(kw.lower() in text for kw in wf["keywords"]):
                trigger_data = {
                    "sender": msg.sender,
                    "sender_name": msg.sender_name,
                    "subject": msg.subject,
                    "body": msg.body[:2000],
                    "message_id": msg.message_id,
                    "thread_id": msg.thread_id,
                    "requested_date": self._extract_date(msg.body),
                }
                run = self._engine.run(
                    workflow_name=wf["name"],
                    trigger_data=trigger_data,
                    trigger_source=msg.sender,
                )
                run_ids.append(run.id)
        return run_ids

    @staticmethod
    def _extract_date(text: str) -> str:
        """Best-effort date extraction from email body. Returns ISO date string."""
        import re
        from datetime import datetime, timedelta

        today = datetime.utcnow()
        lower = text.lower()

        if "tomorrow" in lower:
            return (today + timedelta(days=1)).strftime("%Y-%m-%d")
        if "today" in lower:
            return today.strftime("%Y-%m-%d")

        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for i, day in enumerate(days):
            if day in lower:
                target_weekday = i
                current_weekday = today.weekday()
                days_ahead = (target_weekday - current_weekday) % 7 or 7
                return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

        # Fallback: next business day
        delta = 1 if today.weekday() < 4 else (7 - today.weekday())
        return (today + timedelta(days=delta)).strftime("%Y-%m-%d")
