"""Markdown file task provider (no external dependencies)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from octopus.config import load_config
from octopus.providers.base import TaskProvider


class MarkdownTaskProvider(TaskProvider):
    def __init__(self) -> None:
        path = load_config().tasks.markdown_path
        self._path = Path(path).expanduser()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("# Tasks\n\n")

    def create_task(
        self,
        title: str,
        project: str,
        priority: str = "Normal",
        notes: str = "",
        due_on: str | None = None,
    ) -> str:
        task_id = str(uuid4())[:8]
        due_str = f" (due: {due_on})" if due_on else ""
        lines = [f"\n- [ ] **[{task_id}]** {title}{due_str}"]
        lines.append(f"  - Project: {project} | Priority: {priority}")
        if notes:
            lines.append(f"  - Notes: {notes}")
        with self._path.open("a") as f:
            f.write("\n".join(lines) + "\n")
        return task_id

    def update_task(self, task_id: str, **kwargs) -> None:
        content = self._path.read_text()
        if task_id not in content:
            raise ValueError(f"Task {task_id} not found")
        if kwargs.get("completed"):
            content = content.replace(
                f"- [ ] **[{task_id}]**",
                f"- [x] **[{task_id}]**",
            )
        self._path.write_text(content)
