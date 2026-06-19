"""Skill: SyncTask — push a task to Asana or a local markdown file."""

from __future__ import annotations

from typing import Any

from octopus.arms.arm5_tasks import TaskManager
from octopus.skills.base import BaseSkill


class SyncTaskSkill(BaseSkill):
    def __init__(self) -> None:
        self._tasks = TaskManager()

    def execute(
        self,
        title: str,
        project: str = "Inbox",
        priority: str = "Normal",
        notes: str = "",
        due_on: str | None = None,
    ) -> dict[str, Any]:
        task_id = self._tasks.create(title, project, priority, notes, due_on)
        return {
            "created": True,
            "task_id": task_id,
            "title": title,
            "project": project,
            "priority": priority,
        }

    def tool_schema(self) -> dict:
        return {
            "name": "sync_task",
            "description": "Create a task in Asana (or local markdown) and link it to a project.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title."},
                    "project": {"type": "string", "description": "Project name to assign the task to.", "default": "Inbox"},
                    "priority": {
                        "type": "string",
                        "enum": ["Low", "Normal", "High", "Urgent"],
                        "description": "Task priority level.",
                        "default": "Normal",
                    },
                    "notes": {"type": "string", "description": "Additional notes or context for the task."},
                    "due_on": {"type": "string", "description": "Due date in YYYY-MM-DD format (optional)."},
                },
                "required": ["title"],
            },
        }
