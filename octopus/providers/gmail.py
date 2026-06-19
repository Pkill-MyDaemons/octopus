"""Gmail provider via Google API."""

from __future__ import annotations

import base64
import os
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

from octopus.models import EmailMessage
from octopus.providers.base import EmailProvider

_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]
_TOKEN_PATH = Path.home() / ".config" / "octopus" / "gmail_token.json"
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
                    f"Gmail credentials not found at {_CREDS_PATH}. "
                    "Download OAuth credentials from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(_CREDS_PATH), _SCOPES)
            creds = flow.run_local_server(port=0)
        _TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        _TOKEN_PATH.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)


class GmailProvider(EmailProvider):
    def __init__(self) -> None:
        self._svc = None  # lazy-init so CLI starts fast without auth

    @property
    def svc(self):
        if self._svc is None:
            self._svc = _build_service()
        return self._svc

    def fetch_unread(self, max_results: int = 20) -> list[EmailMessage]:
        results = (
            self.svc.users()
            .messages()
            .list(userId="me", q="is:unread", maxResults=max_results)
            .execute()
        )
        messages = []
        for item in results.get("messages", []):
            msg = self.svc.users().messages().get(userId="me", id=item["id"], format="full").execute()
            messages.append(self._parse(msg))
        return messages

    def send(self, to: str, subject: str, body: str, thread_id: str | None = None) -> str:
        mime = MIMEText(body)
        mime["to"] = to
        mime["subject"] = subject
        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
        payload: dict = {"raw": raw}
        if thread_id:
            payload["threadId"] = thread_id
        sent = self.svc.users().messages().send(userId="me", body=payload).execute()
        return sent["id"]

    def mark_read(self, message_id: str) -> None:
        self.svc.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["UNREAD"]},
        ).execute()

    @staticmethod
    def _parse(msg: dict) -> EmailMessage:
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        body = ""
        payload = msg.get("payload", {})
        if "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
        elif "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain" and part["body"].get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                    break

        sender_raw = headers.get("From", "")
        if "<" in sender_raw:
            sender_name, sender_email = sender_raw.split("<", 1)
            sender_email = sender_email.rstrip(">").strip()
            sender_name = sender_name.strip().strip('"')
        else:
            sender_email = sender_raw
            sender_name = sender_raw

        return EmailMessage(
            message_id=msg["id"],
            sender=sender_email,
            sender_name=sender_name,
            subject=headers.get("Subject", "(no subject)"),
            body=body,
            received_at=datetime.fromtimestamp(int(msg["internalDate"]) / 1000),
            thread_id=msg.get("threadId"),
        )
