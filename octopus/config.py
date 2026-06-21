"""Configuration loading and management."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 4096


class EmailConfig(BaseModel):
    provider: str = "gmail"
    poll_interval_seconds: int = 300


class CalendarConfig(BaseModel):
    provider: str = "google_calendar"
    no_meetings_before: str = "09:00"
    no_meetings_after: str = "18:00"
    slot_duration_minutes: int = 30


class TasksConfig(BaseModel):
    provider: str = "markdown"
    markdown_path: str = "~/tasks.md"
    asana_workspace: str = ""


class MemoryConfig(BaseModel):
    provider: str = "chromadb"
    persist_dir: str = "~/.config/octopus/memory"


class NotificationsConfig(BaseModel):
    provider: str = "system"
    slack_webhook: str = ""


class SandboxConfig(BaseModel):
    db_path: str = "~/.config/octopus/sandbox.db"
    auto_expire_hours: int = 24


class SecurityConfig(BaseModel):
    max_prompt_length: int = 8192
    injection_block_patterns: list[str] = Field(default_factory=lambda: [
        "ignore previous instructions",
        "ignore all prior",
        "disregard your",
        "you are now",
        "act as if",
        "pretend you are",
    ])
    redact_pii: bool = True


class OctopusConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)
    calendar: CalendarConfig = Field(default_factory=CalendarConfig)
    tasks: TasksConfig = Field(default_factory=TasksConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)


def _config_paths() -> list[Path]:
    """Return candidate config file locations, highest priority first."""
    candidates = []
    if env := os.environ.get("OCTOPUS_CONFIG"):
        candidates.append(Path(env))
    candidates.append(Path.home() / ".config" / "octopus" / "settings.yaml")
    candidates.append(Path(__file__).parent.parent / "config" / "settings.yaml")
    return candidates


@lru_cache(maxsize=1)
def load_config() -> OctopusConfig:
    load_dotenv(Path.home() / ".config" / "octopus" / ".env")
    raw: dict[str, Any] = {}
    for path in _config_paths():
        if path.exists():
            with path.open() as f:
                raw = yaml.safe_load(f) or {}
            break
    return OctopusConfig.model_validate(raw)
