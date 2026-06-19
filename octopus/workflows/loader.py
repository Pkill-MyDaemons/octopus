"""Load workflow definitions from YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Search order: user workflows dir, then built-in definitions
_SEARCH_PATHS = [
    Path.home() / ".config" / "octopus" / "workflows",
    Path(__file__).parent.parent.parent / "workflows",
]


def load_workflow(name: str) -> dict[str, Any]:
    """Load a workflow by name from YAML. Raises FileNotFoundError if not found."""
    for base in _SEARCH_PATHS:
        path = base / f"{name}.yaml"
        if path.exists():
            with path.open() as f:
                return yaml.safe_load(f)
    raise FileNotFoundError(
        f"Workflow {name!r} not found. Searched: {[str(p) for p in _SEARCH_PATHS]}"
    )


def list_workflows() -> list[str]:
    """Return names of all available workflows."""
    seen: set[str] = set()
    names: list[str] = []
    for base in _SEARCH_PATHS:
        if base.exists():
            for path in sorted(base.glob("*.yaml")):
                n = path.stem
                if n not in seen:
                    seen.add(n)
                    names.append(n)
    return names
