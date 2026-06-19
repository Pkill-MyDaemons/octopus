"""Asana task provider."""

from __future__ import annotations

import os

from octopus.config import load_config
from octopus.providers.base import TaskProvider


class AsanaProvider(TaskProvider):
    def __init__(self) -> None:
        import asana
        token = os.environ.get("ASANA_TOKEN", "")
        if not token:
            raise RuntimeError("ASANA_TOKEN environment variable is not set.")
        self._client = asana.Client.access_token(token)
        self._workspace = load_config().tasks.asana_workspace

    def create_task(
        self,
        title: str,
        project: str,
        priority: str = "Normal",
        notes: str = "",
        due_on: str | None = None,
    ) -> str:
        project_gid = self._resolve_project(project)
        params = {
            "name": title,
            "notes": notes,
            "projects": [project_gid],
            "workspace": self._workspace,
        }
        if due_on:
            params["due_on"] = due_on
        task = self._client.tasks.create_task(params)
        return task["gid"]

    def update_task(self, task_id: str, **kwargs) -> None:
        self._client.tasks.update_task(task_id, kwargs)

    def _resolve_project(self, name: str) -> str:
        projects = self._client.projects.find_all({"workspace": self._workspace})
        for p in projects:
            if p["name"].lower() == name.lower():
                return p["gid"]
        raise ValueError(f"Asana project {name!r} not found in workspace {self._workspace!r}")
