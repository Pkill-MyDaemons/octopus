"""Arm 5 — Task Manager: creates and updates tasks in Asana or markdown."""

from __future__ import annotations

from octopus.config import load_config
from octopus.providers import get_task_provider


class TaskManager:
    def __init__(self) -> None:
        self._provider = get_task_provider(load_config().tasks.provider)

    def create(
        self,
        title: str,
        project: str = "Inbox",
        priority: str = "Normal",
        notes: str = "",
        due_on: str | None = None,
    ) -> str:
        return self._provider.create_task(title, project, priority, notes, due_on)

    def complete(self, task_id: str) -> None:
        self._provider.update_task(task_id, completed=True)

    def update(self, task_id: str, **kwargs) -> None:
        self._provider.update_task(task_id, **kwargs)
