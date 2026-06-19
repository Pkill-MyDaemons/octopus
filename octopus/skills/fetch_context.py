"""Skill: FetchContext — query the memory bank for a person or project."""

from __future__ import annotations

from typing import Any

from octopus.arms.arm7_memory import MemoryBank
from octopus.skills.base import BaseSkill


class FetchContextSkill(BaseSkill):
    def __init__(self) -> None:
        self._memory = MemoryBank()

    def execute(self, entity: str, query: str | None = None, top_k: int = 5) -> dict[str, Any]:
        q = query or entity
        entries = self._memory.recall(q, entity=entity, top_k=top_k)
        summary = self._memory.get_entity_summary(entity, top_k=top_k)
        priority = "high" if any("vip" in e.content.lower() or "client" in e.content.lower() for e in entries) else "normal"
        return {
            "entity": entity,
            "memory_count": len(entries),
            "summary": summary,
            "priority": priority,
            "entries": [{"content": e.content, "created_at": e.created_at.isoformat()} for e in entries],
        }

    def tool_schema(self) -> dict:
        return {
            "name": "fetch_memory_context",
            "description": "Retrieve stored memories and context about a specific person or project from the local vector database (Arm 7).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "entity": {
                        "type": "string",
                        "description": "The name of the person, project, or topic to recall context for.",
                    },
                    "query": {
                        "type": "string",
                        "description": "Optional semantic query to narrow the search. Defaults to the entity name.",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of memory entries to retrieve (default: 5).",
                        "default": 5,
                    },
                },
                "required": ["entity"],
            },
        }
