"""Arm 4 — Sandbox: the air-gap between agent decisions and the real world."""

from octopus.security.sandbox import ActionSandbox

# Arm 4 is a thin alias — the sandbox implementation lives in security/sandbox.py
# to keep security primitives separate from arm orchestration.
__all__ = ["ActionSandbox"]
