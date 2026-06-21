"""Skill: run a shell command inside the configured execution sandbox."""

from __future__ import annotations

from typing import Any

from octopus.skills.base import BaseSkill


class RunShellSkill(BaseSkill):
    def execute(self, command: str, timeout: int | None = None, **_) -> dict[str, Any]:
        from octopus.config import load_config
        from octopus.security.exec_sandbox import build_executor

        cfg = load_config().exec_sandbox
        executor = build_executor(
            cfg.driver,
            image=cfg.docker_image,
            memory=cfg.docker_memory,
            cpus=cfg.docker_cpus,
        )
        result = executor.run(command, timeout=timeout or cfg.timeout_seconds)
        return result.to_dict()

    def tool_schema(self) -> dict:
        return {
            "name": "run_shell",
            "description": (
                "Run a shell command in the configured execution sandbox "
                "(docker, sandbox-exec, or none). Returns stdout, stderr, and returncode."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Override the default timeout in seconds.",
                    },
                },
                "required": ["command"],
            },
        }
