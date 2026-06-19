"""Google Calendar provider."""

from __future__ import annotations

from datetime import datetime, timedelta, time
from pathlib import Path

from octopus.config import load_config
from octopus.models import CalendarSlot
from octopus.providers.base import CalendarProvider

_SCOPES = ["https://www.googleapis.com/auth/calendar"]
_TOKEN_PATH = Path.home() / ".config" / "octopus" / "gcal_token.json"
_CREDS_PATH = Path.home() / ".config" / "octopus" / "gmail_credentials.json"


def _build_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if _TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(_TOKEN_PATH), _SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not _CREDS_PATH.exists():
                raise RuntimeError(
                    f"Google credentials not found at {_CREDS_PATH}. "
                    "Download OAuth credentials from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(_CREDS_PATH), _SCOPES)
            creds = flow.run_local_server(port=0)
        _TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        _TOKEN_PATH.write_text(creds.to_json())
    return build("calendar", "v3", credentials=creds)


class GoogleCalendarProvider(CalendarProvider):
    def __init__(self) -> None:
        self._svc = None

    @property
    def svc(self):
        if self._svc is None:
            self._svc = _build_service()
        return self._svc

    def list_events(self, start: datetime, end: datetime) -> list[dict]:
        result = (
            self.svc.events()
            .list(
                calendarId="primary",
                timeMin=start.isoformat() + "Z",
                timeMax=end.isoformat() + "Z",
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return result.get("items", [])

    def find_free_slots(
        self,
        date: datetime,
        duration_minutes: int,
        earliest: str = "09:00",
        latest: str = "18:00",
    ) -> list[CalendarSlot]:
        cfg = load_config().calendar
        earliest = earliest or cfg.no_meetings_before
        latest = latest or cfg.no_meetings_after

        e_h, e_m = map(int, earliest.split(":"))
        l_h, l_m = map(int, latest.split(":"))

        day_start = date.replace(hour=e_h, minute=e_m, second=0, microsecond=0)
        day_end = date.replace(hour=l_h, minute=l_m, second=0, microsecond=0)

        events = self.list_events(day_start, day_end)
        busy: list[tuple[datetime, datetime]] = []
        for ev in events:
            s = ev.get("start", {})
            en = ev.get("end", {})
            if "dateTime" in s:
                busy.append((
                    datetime.fromisoformat(s["dateTime"].replace("Z", "+00:00")).replace(tzinfo=None),
                    datetime.fromisoformat(en["dateTime"].replace("Z", "+00:00")).replace(tzinfo=None),
                ))

        slots: list[CalendarSlot] = []
        cursor = day_start
        delta = timedelta(minutes=duration_minutes)
        while cursor + delta <= day_end:
            slot_end = cursor + delta
            overlap = any(b_s < slot_end and b_e > cursor for b_s, b_e in busy)
            if not overlap:
                slots.append(CalendarSlot(start=cursor, end=slot_end, status="free"))
            cursor += delta
        return slots

    def hold_slot(self, slot: CalendarSlot, title: str = "Tentative Hold") -> str:
        body = {
            "summary": title,
            "start": {"dateTime": slot.start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": slot.end.isoformat(), "timeZone": "UTC"},
            "status": "tentative",
        }
        event = self.svc.events().insert(calendarId="primary", body=body).execute()
        return event["id"]

    def confirm_event(self, event_id: str, title: str, attendees: list[str]) -> str:
        body = {
            "summary": title,
            "status": "confirmed",
            "attendees": [{"email": a} for a in attendees],
        }
        event = (
            self.svc.events()
            .patch(calendarId="primary", eventId=event_id, body=body)
            .execute()
        )
        return event["id"]

    def delete_event(self, event_id: str) -> None:
        self.svc.events().delete(calendarId="primary", eventId=event_id).execute()
