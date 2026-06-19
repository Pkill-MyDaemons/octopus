"""Skill: ProposeSlots — find calendar availability for a meeting."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from octopus.arms.arm2_calendar import CalendarReader
from octopus.arms.arm3_scheduler import SlotScheduler
from octopus.models import CalendarSlot
from octopus.skills.base import BaseSkill


class ProposeSlotsSkill(BaseSkill):
    def __init__(self) -> None:
        self._reader = CalendarReader()
        self._scheduler = SlotScheduler()

    def execute(
        self,
        date: str,
        duration_minutes: int = 30,
        max_slots: int = 3,
        hold_tentative: bool = True,
    ) -> dict[str, Any]:
        target = datetime.fromisoformat(date)
        slots = self._reader.find_free_slots(target, duration_minutes)[:max_slots]

        held_ids: list[str] = []
        if hold_tentative:
            held_ids = self._scheduler.hold_multiple(slots, "Tentative Hold (Octopus)")

        return {
            "date": date,
            "duration_minutes": duration_minutes,
            "slots": [
                {
                    "start": s.start.strftime("%I:%M %p"),
                    "end": s.end.strftime("%I:%M %p"),
                    "start_iso": s.start.isoformat(),
                    "end_iso": s.end.isoformat(),
                    "event_id": eid,
                }
                for s, eid in zip(slots, held_ids or [""] * len(slots))
            ],
            "count": len(slots),
        }

    def tool_schema(self) -> dict:
        return {
            "name": "propose_slots",
            "description": "Scan the user's calendar for available meeting slots on a given date, block them as tentative, and return the options.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "ISO 8601 date to search (e.g. '2026-06-19'). Time component is ignored.",
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Length of the meeting in minutes (default: 30).",
                        "default": 30,
                    },
                    "max_slots": {
                        "type": "integer",
                        "description": "Maximum number of slots to return (default: 3).",
                        "default": 3,
                    },
                    "hold_tentative": {
                        "type": "boolean",
                        "description": "Whether to immediately place tentative holds on found slots (default: true).",
                        "default": True,
                    },
                },
                "required": ["date"],
            },
        }
