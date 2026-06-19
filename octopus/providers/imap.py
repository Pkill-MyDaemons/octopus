"""IMAP email provider for non-Gmail accounts."""

from __future__ import annotations

import email
import imaplib
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText

from octopus.models import EmailMessage
from octopus.providers.base import EmailProvider


class IMAPProvider(EmailProvider):
    """Generic IMAP/SMTP provider. Configure via environment variables:
      IMAP_HOST, IMAP_PORT, SMTP_HOST, SMTP_PORT, EMAIL_USER, EMAIL_PASS
    """

    def __init__(self) -> None:
        self._imap_host = os.environ.get("IMAP_HOST", "")
        self._imap_port = int(os.environ.get("IMAP_PORT", "993"))
        self._smtp_host = os.environ.get("SMTP_HOST", "")
        self._smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self._user = os.environ.get("EMAIL_USER", "")
        self._password = os.environ.get("EMAIL_PASS", "")

    def fetch_unread(self, max_results: int = 20) -> list[EmailMessage]:
        conn = imaplib.IMAP4_SSL(self._imap_host, self._imap_port)
        conn.login(self._user, self._password)
        conn.select("INBOX")
        _, data = conn.search(None, "UNSEEN")
        ids = data[0].split()[-max_results:]
        messages = []
        for uid in ids:
            _, msg_data = conn.fetch(uid, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            messages.append(self._parse(uid.decode(), msg))
        conn.logout()
        return messages

    def send(self, to: str, subject: str, body: str, thread_id: str | None = None) -> str:
        mime = MIMEText(body)
        mime["From"] = self._user
        mime["To"] = to
        mime["Subject"] = subject
        with smtplib.SMTP(self._smtp_host, self._smtp_port) as s:
            s.starttls()
            s.login(self._user, self._password)
            s.sendmail(self._user, [to], mime.as_string())
        return ""  # IMAP UID of sent message not easily retrievable

    def mark_read(self, message_id: str) -> None:
        conn = imaplib.IMAP4_SSL(self._imap_host, self._imap_port)
        conn.login(self._user, self._password)
        conn.select("INBOX")
        conn.store(message_id, "+FLAGS", "\\Seen")
        conn.logout()

    @staticmethod
    def _parse(uid: str, msg: email.message.Message) -> EmailMessage:
        sender = msg.get("From", "")
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    break
        else:
            body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

        date_str = msg.get("Date", "")
        try:
            from email.utils import parsedate_to_datetime
            received_at = parsedate_to_datetime(date_str)
        except Exception:
            received_at = datetime.utcnow()

        return EmailMessage(
            message_id=uid,
            sender=sender,
            sender_name=sender,
            subject=msg.get("Subject", "(no subject)"),
            body=body,
            received_at=received_at,
            thread_id=msg.get("Message-ID"),
        )
