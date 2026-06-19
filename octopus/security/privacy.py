"""PII redaction and privacy guardrails."""

from __future__ import annotations

import re


_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")),
    ("phone", re.compile(r"\b(\+?1[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b")),
    ("ssn",   re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("cc",    re.compile(r"\b(?:\d[ -]?){13,16}\b")),
]


class PrivacyFilter:
    """Redacts PII from text before it is stored in memory or logs."""

    def redact(self, text: str) -> str:
        for label, pattern in _PATTERNS:
            text = pattern.sub(f"[REDACTED:{label.upper()}]", text)
        return text

    def contains_pii(self, text: str) -> bool:
        return any(p.search(text) for _, p in _PATTERNS)
