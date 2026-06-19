"""Shared domain models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    SEND_EMAIL = "send_email"
    REPLY_EMAIL = "reply_email"
    CREATE_CALENDAR_EVENT = "create_calendar_event"
    HOLD_CALENDAR_SLOTS = "hold_calendar_slots"
    CREATE_TASK = "create_task"
    UPDATE_TASK = "update_task"
    SEND_NOTIFICATION = "send_notification"


class SandboxAction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    action_type: ActionType
    payload: dict[str, Any]
    workflow_id: str
    workflow_name: str
    triggered_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved: bool | None = None
    executed_at: datetime | None = None


class EmailMessage(BaseModel):
    message_id: str
    sender: str
    sender_name: str
    subject: str
    body: str
    received_at: datetime
    thread_id: str | None = None


class CalendarSlot(BaseModel):
    start: datetime
    end: datetime
    status: str = "free"  # free | tentative | busy


class MemoryEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    entity: str          # person, project, etc.
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WorkflowRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_name: str
    trigger_source: str
    trigger_data: dict[str, Any]
    status: str = "running"  # running | paused | completed | failed | rejected
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    sandbox_actions: list[SandboxAction] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
