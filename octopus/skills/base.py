"""Base class for all skills."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseSkill(ABC):
    @abstractmethod
    def execute(self, **kwargs) -> dict[str, Any]:
        """Run the skill and return a result dict."""
        ...

    @abstractmethod
    def tool_schema(self) -> dict:
        """Return an Anthropic-compatible tool schema for function calling."""
        ...

    def name(self) -> str:
        return self.tool_schema()["name"]
