"""Prompt injection detection and mitigation."""

from __future__ import annotations

import re
from dataclasses import dataclass

from octopus.config import SecurityConfig, load_config


@dataclass
class InjectionResult:
    safe: bool
    reason: str | None = None
    sanitized: str | None = None


class InjectionGuard:
    """Detects and blocks prompt injection attempts in external content."""

    # Delimiters that can be used to escape context
    _ESCAPE_PATTERNS = [
        r"```[^\n]*\n.*?```",          # fenced code blocks trying to embed instructions
        r"<\s*system\s*>.*?<\s*/\s*system\s*>",  # fake system tags
        r"\[INST\].*?\[/INST\]",       # Llama-style instruction tags
        r"###\s*(System|Human|Assistant)\s*:",     # chat format injection
    ]

    def __init__(self, config: SecurityConfig | None = None) -> None:
        self._cfg = config or load_config().security
        self._block_patterns = [
            re.compile(p, re.IGNORECASE | re.DOTALL)
            for p in self._cfg.injection_block_patterns
        ]
        self._escape_patterns = [
            re.compile(p, re.IGNORECASE | re.DOTALL)
            for p in self._ESCAPE_PATTERNS
        ]

    def check(self, text: str) -> InjectionResult:
        """Return safe=False if the text looks like a prompt injection attempt."""
        if len(text) > self._cfg.max_prompt_length:
            return InjectionResult(
                safe=False,
                reason=f"Content exceeds maximum allowed length ({self._cfg.max_prompt_length} chars)",
            )

        for pattern in self._block_patterns:
            if pattern.search(text):
                return InjectionResult(
                    safe=False,
                    reason=f"Blocked injection pattern detected: '{pattern.pattern}'",
                )

        for pattern in self._escape_patterns:
            if pattern.search(text):
                return InjectionResult(
                    safe=False,
                    reason=f"Structural injection attempt detected",
                )

        return InjectionResult(safe=True, sanitized=self._sanitize(text))

    def _sanitize(self, text: str) -> str:
        """Strip known dangerous markup while preserving content."""
        # Wrap external content so the LLM treats it as data, not instructions
        return f"[EXTERNAL CONTENT START]\n{text}\n[EXTERNAL CONTENT END]"

    def wrap_for_llm(self, label: str, content: str) -> str:
        """Safely embed external data (email body, etc.) in an LLM prompt."""
        result = self.check(content)
        if not result.safe:
            raise ValueError(f"Injection guard blocked {label}: {result.reason}")
        return f'<{label} trust="external">\n{result.sanitized}\n</{label}>'
