"""Skill: DraftEmailTemplate — fill a named template and stage the result."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from octopus.models import ActionType, SandboxAction
from octopus.security.sandbox import ActionSandbox
from octopus.skills.base import BaseSkill

_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"

_BUILTIN_TEMPLATES: dict[str, str] = {
    "intro_deck": (
        "Hi {name},\n\n"
        "Thanks for reaching out! I'd love to share more about what we do.\n\n"
        "I'm attaching our intro deck — it covers our core offerings and a few "
        "case studies that might be relevant to you.\n\n"
        "Happy to hop on a call to walk through it. Let me know what works!\n\n"
        "Best,\n{sender_name}"
    ),
    "meeting_confirmation": (
        "Hi {name},\n\n"
        "Looking forward to our call on {date} at {time}.\n\n"
        "I'll send a calendar invite shortly. Talk soon!\n\n"
        "Best,\n{sender_name}"
    ),
    "follow_up": (
        "Hi {name},\n\n"
        "Just following up on my previous email — wanted to make sure it didn't "
        "get lost in the shuffle.\n\n"
        "Let me know if you have any questions!\n\n"
        "Best,\n{sender_name}"
    ),
}


class DraftEmailTemplateSkill(BaseSkill):
    def __init__(self) -> None:
        self._sandbox = ActionSandbox()

    def execute(
        self,
        template_id: str,
        to: str,
        variables: dict[str, str] | None = None,
        workflow_id: str = "manual",
        workflow_name: str = "Template Draft",
        triggered_by: str = "",
    ) -> dict[str, Any]:
        body = self._render(template_id, variables or {})
        subject = f"Re: {variables.get('subject', '')}" if variables else "Re: Your inquiry"
        action = SandboxAction(
            action_type=ActionType.SEND_EMAIL,
            payload={"to": to, "subject": subject, "body": body},
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            triggered_by=triggered_by,
        )
        self._sandbox.stage(action)
        return {
            "staged": True,
            "action_id": action.id,
            "template_id": template_id,
            "to": to,
            "preview": body[:200],
        }

    def _render(self, template_id: str, variables: dict[str, str]) -> str:
        template = _BUILTIN_TEMPLATES.get(template_id)
        if template is None:
            # Try loading from disk
            path = _TEMPLATES_DIR / f"{template_id}.txt"
            if path.exists():
                template = path.read_text()
            else:
                raise ValueError(f"Unknown template: {template_id!r}")
        return template.format_map(variables)

    def tool_schema(self) -> dict:
        return {
            "name": "draft_email_template",
            "description": "Fill a named email template with variables and stage the result in the sandbox.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "template_id": {
                        "type": "string",
                        "description": "Template name. Built-ins: intro_deck, meeting_confirmation, follow_up.",
                    },
                    "to": {"type": "string", "description": "Recipient email address."},
                    "variables": {
                        "type": "object",
                        "description": "Key/value pairs to substitute into the template (e.g. {name}, {date}).",
                        "additionalProperties": {"type": "string"},
                    },
                    "workflow_id": {"type": "string"},
                    "workflow_name": {"type": "string"},
                    "triggered_by": {"type": "string"},
                },
                "required": ["template_id", "to"],
            },
        }
