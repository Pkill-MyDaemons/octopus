"""Skill registry — maps skill names to their implementations and tool schemas."""

from __future__ import annotations

from octopus.skills.fetch_context import FetchContextSkill
from octopus.skills.propose_slots import ProposeSlotsSkill
from octopus.skills.stage_draft import StageDraftSkill
from octopus.skills.sync_task import SyncTaskSkill
from octopus.skills.send_to_sandbox import SendToSandboxSkill
from octopus.skills.draft_email_template import DraftEmailTemplateSkill
from octopus.skills.run_shell import RunShellSkill

_REGISTRY: dict[str, type] = {
    "fetch_memory_context": FetchContextSkill,
    "propose_slots": ProposeSlotsSkill,
    "stage_draft": StageDraftSkill,
    "sync_task": SyncTaskSkill,
    "send_to_sandbox": SendToSandboxSkill,
    "draft_email_template": DraftEmailTemplateSkill,
    "run_shell": RunShellSkill,
}


def get_skill(name: str):
    cls = _REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"Unknown skill: {name!r}. Available: {list(_REGISTRY)}")
    return cls()


def all_tool_schemas() -> list[dict]:
    """Return Anthropic tool-use schemas for every registered skill.

    Uses a lightweight stub instantiation path — providers are lazy-loaded
    so this is safe to call without credentials configured.
    """
    schemas = []
    for name, cls in _REGISTRY.items():
        # Create a bare instance without triggering provider __init__ side-effects.
        # Each skill's tool_schema() must be callable without network/db access.
        obj = object.__new__(cls)
        schemas.append(obj.tool_schema())
    return schemas
