"""Skill: StageDraft — compose an email reply and hold it in the sandbox."""

from __future__ import annotations

from typing import Any

from octopus.models import ActionType, SandboxAction
from octopus.security.sandbox import ActionSandbox
from octopus.skills.base import BaseSkill


class StageDraftSkill(BaseSkill):
    def __init__(self) -> None:
        self._sandbox = ActionSandbox()

    def execute(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: str | None = None,
        workflow_id: str = "manual",
        workflow_name: str = "Manual Draft",
        triggered_by: str = "",
    ) -> dict[str, Any]:
        action = SandboxAction(
            action_type=ActionType.REPLY_EMAIL,
            payload={
                "to": to,
                "subject": subject,
                "body": body,
                "thread_id": thread_id,
            },
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            triggered_by=triggered_by,
        )
        self._sandbox.stage(action)
        return {
            "staged": True,
            "action_id": action.id,
            "to": to,
            "subject": subject,
            "preview": body[:200] + ("..." if len(body) > 200 else ""),
        }

    def tool_schema(self) -> dict:
        return {
            "name": "stage_draft",
            "description": "Write an email reply and deposit it in the sandbox queue (Arm 4). The email is NOT sent until the user approves it.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address."},
                    "subject": {"type": "string", "description": "Email subject line."},
                    "body": {"type": "string", "description": "Full email body text."},
                    "thread_id": {
                        "type": "string",
                        "description": "Gmail thread ID to reply within (optional).",
                    },
                    "workflow_id": {"type": "string", "description": "ID of the triggering workflow."},
                    "workflow_name": {"type": "string", "description": "Human-readable workflow name."},
                    "triggered_by": {"type": "string", "description": "Source identifier (e.g. sender email)."},
                },
                "required": ["to", "subject", "body"],
            },
        }
