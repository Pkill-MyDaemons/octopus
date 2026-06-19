"""Workflow engine — executes deterministic and dynamic (LLM-driven) workflows."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from octopus.models import WorkflowRun
from octopus.skills import get_skill
from octopus.workflows.loader import load_workflow


class WorkflowEngine:
    """Executes workflow definitions step by step.

    Deterministic mode: follows the `steps` list in order.
    Dynamic mode: lets the LLM decide the next step based on context.
    """

    def __init__(self, brain=None) -> None:
        # brain is the LLM orchestration layer (injected to avoid circular imports)
        self._brain = brain

    def run(
        self,
        workflow_name: str,
        trigger_data: dict[str, Any],
        trigger_source: str = "",
    ) -> WorkflowRun:
        definition = load_workflow(workflow_name)
        run = WorkflowRun(
            id=str(uuid4()),
            workflow_name=workflow_name,
            trigger_source=trigger_source,
            trigger_data=trigger_data,
        )

        mode = definition.get("mode", "deterministic")
        if mode == "dynamic" and self._brain:
            return self._run_dynamic(run, definition, trigger_data)
        return self._run_deterministic(run, definition, trigger_data)

    def _run_deterministic(
        self,
        run: WorkflowRun,
        definition: dict[str, Any],
        trigger_data: dict[str, Any],
    ) -> WorkflowRun:
        context: dict[str, Any] = {"trigger": trigger_data, "run_id": run.id}

        for step in definition.get("steps", []):
            skill_name = step.get("use_skill")
            if not skill_name:
                continue

            args = dict(step.get("args", {}))
            # Interpolate {{context.key}} references
            args = self._interpolate(args, context)
            # Always pass workflow metadata to skills that accept it
            for key in ("workflow_id", "workflow_name", "triggered_by"):
                if key not in args:
                    if key == "workflow_id":
                        args[key] = run.id
                    elif key == "workflow_name":
                        args[key] = run.workflow_name
                    elif key == "triggered_by":
                        args[key] = run.trigger_source

            skill = get_skill(skill_name)
            result = skill.execute(**args)
            context[skill_name] = result

            # If workflow is paused (sandbox notification sent), stop here
            if result.get("paused"):
                run.status = "paused"
                run.context = context
                return run

        run.status = "completed"
        run.context = context
        return run

    def _run_dynamic(
        self,
        run: WorkflowRun,
        definition: dict[str, Any],
        trigger_data: dict[str, Any],
    ) -> WorkflowRun:
        """Let the LLM orchestrate which skills to invoke based on outcomes."""
        context: dict[str, Any] = {"trigger": trigger_data, "run_id": run.id}
        system_prompt = definition.get("system_prompt", "")
        goal = definition.get("goal", "Complete the workflow.")

        messages = [
            {
                "role": "user",
                "content": (
                    f"Workflow goal: {goal}\n\n"
                    f"Trigger data: {json.dumps(trigger_data, indent=2)}\n\n"
                    "Use the available tools to complete this workflow. "
                    "Call `send_to_sandbox` when actions are ready for user approval."
                ),
            }
        ]

        result = self._brain.run_with_tools(
            messages=messages,
            system=system_prompt,
            extra_context={"workflow_id": run.id, "workflow_name": run.workflow_name},
        )
        run.status = "paused" if result.get("paused") else "completed"
        run.context = {**context, **result}
        return run

    @staticmethod
    def _interpolate(args: dict, context: dict) -> dict:
        """Replace {{key}} and {{step.key}} placeholders with context values."""
        import re

        def _replace(val):
            if not isinstance(val, str):
                return val
            def sub(m):
                path = m.group(1).split(".")
                node = context
                for p in path:
                    if isinstance(node, dict):
                        node = node.get(p, m.group(0))
                    else:
                        return m.group(0)
                return str(node)
            return re.sub(r"\{\{(.+?)\}\}", sub, val)

        return {k: _replace(v) for k, v in args.items()}
