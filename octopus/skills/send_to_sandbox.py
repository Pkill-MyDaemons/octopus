"""Skill: SendToSandbox — flush all workflow actions to the sandbox and pause."""

from __future__ import annotations

from typing import Any

from octopus.arms.arm6_notify import Notifier
from octopus.skills.base import BaseSkill


class SendToSandboxSkill(BaseSkill):
    def __init__(self) -> None:
        self._notifier = Notifier()

    def execute(self, workflow_id: str, workflow_name: str, action_count: int = 1) -> dict[str, Any]:
        self._notifier.send(
            title=f"Octopus: {workflow_name}",
            message=f"{action_count} action(s) ready for your review. Run `octopus review` to approve.",
        )
        return {
            "paused": True,
            "workflow_id": workflow_id,
            "message": f"Workflow paused. {action_count} action(s) in sandbox. Run `octopus review`.",
        }

    def tool_schema(self) -> dict:
        return {
            "name": "send_to_sandbox",
            "description": "Pause the workflow and notify the user that staged actions are ready for review. Sends a desktop notification.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "ID of the current workflow run."},
                    "workflow_name": {"type": "string", "description": "Human-readable workflow name."},
                    "action_count": {"type": "integer", "description": "Number of staged actions awaiting approval.", "default": 1},
                },
                "required": ["workflow_id", "workflow_name"],
            },
        }
