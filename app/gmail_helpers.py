from __future__ import annotations
import base64
from email.message import EmailMessage
from pathlib import Path
from typing import Optional, Tuple


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="ignore")


def extract_headers(payload: dict) -> dict:
    return {h["name"].lower(): h["value"] for h in payload.get("headers", [])}


def get_message_body(payload: dict) -> str:
    mt = payload.get("mimeType", "")
    if mt in ("text/plain", "text/html"):
        data = payload.get("body", {}).get("data")
        return _decode(data) if data else ""

    for part in payload.get("parts", []) or []:
        if part.get("mimeType") in ("text/plain", "text/html"):
            data = part.get("body", {}).get("data")
            return _decode(data) if data else ""

    # nested fallback
    for part in payload.get("parts", []) or []:
        for sub in part.get("parts", []) or []:
            if sub.get("mimeType") in ("text/plain", "text/html"):
                data = sub.get("body", {}).get("data")
                return _decode(data) if data else ""

    return ""


def send_email_with_pdf(
    svc,
    to_email: str,
    subject: str,
    body_text: str,
    pdf_path: Path,
    thread_id: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Sends an email via Gmail API with a PDF attachment.
    Returns: (sent_message_id, thread_id)
    """
    msg = EmailMessage()
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body_text)

    pdf_bytes = pdf_path.read_bytes()
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=pdf_path.name)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    req_body = {"raw": raw}
    if thread_id:
        req_body["threadId"] = thread_id

    sent = svc.users().messages().send(userId="me", body=req_body).execute()
    return sent["id"], sent["threadId"]


from email.mime.text import MIMEText
import base64


def send_followup_in_thread(svc, to_email, subject, body_text, thread_id):
    msg = MIMEText(body_text)
    msg["to"] = to_email
    msg["subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    res = svc.users().messages().send(
        userId="me",
        body={"raw": raw, "threadId": thread_id}
    ).execute()

    return res.get("id")
