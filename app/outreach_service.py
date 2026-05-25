from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path
import csv
from datetime import datetime, timedelta
from app.sheet_settings import load_settings

from app.config import FOLLOWUP_DAYS, CV_PDF_PATH
from app.gmail_helpers import send_email_with_pdf
from app.db import get_conn

def load_recipients(csv_path: Path):
    recs = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("to_email"):
                recs.append({
                    "to_email": row["to_email"].strip(),
                    "to_name": (row.get("to_name") or "").strip() or "there"
                })
    return recs

def build_first_email(template_text: str, to_name: str, job: dict):
    company = job.get("company") or "your company"
    title = job.get("title") or "the role"
    body = template_text.format(
        name=to_name,
        title=title,
        company=company,
    )
    subject = f"Application: {title} — Umar"
    return subject, body

def send_for_latest_jobs(svc, recipients_csv: Path, template_path: Path, max_jobs: int = 5, max_recipients: int = 5):
    recipients = load_recipients(recipients_csv)
    recipients = recipients[:max_recipients]

    template_text = template_path.read_text(encoding="utf-8")

    sent_rows = []

    with get_conn() as conn:
        cur = conn.cursor()

        # pick latest jobs (you can improve selection logic later)
        cur.execute("""
            SELECT id, title, company, location, link
            FROM jobs
            ORDER BY received_at DESC
            LIMIT ?
        """, (max_jobs,))
        jobs = cur.fetchall()

        now = datetime.now()
        for job_row in jobs:
            job = {
                "id": job_row[0],
                "title": job_row[1],
                "company": job_row[2],
                "location": job_row[3],
                "link": job_row[4],
            }
            settings = load_settings()
followup_days = settings["followup_days"]

due = datetime.now() + timedelta(days=followup_days)
followup_due_at = due.replace(
    hour=settings["followup_hour"],
    minute=settings["followup_minute"],
    second=0,
    microsecond=0
)

            for rec in recipients:
                to_email = rec["to_email"]
                to_name = rec["to_name"]

                subject, body = build_first_email(template_text, to_name, job)

                # send email
                sent_message_id, thread_id = send_email_with_pdf(
                    svc,
                    to_email=to_email,
                    subject=subject,
                    body_text=body,
                    pdf_path=CV_PDF_PATH,
                    thread_id=None
                )

                sent_at = now.isoformat()
                followup_due_at = (now + timedelta(days=FOLLOWUP_DAYS)).isoformat()

                cur.execute("""
                    INSERT INTO outreach
                    (job_id, to_email, to_name, subject, sent_at, followup_due_at, status, gmail_thread_id, gmail_sent_message_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job["id"],
                    to_email,
                    to_name,
                    subject,
                    sent_at,
                    followup_due_at,
                    "SENT",
                    thread_id,
                    sent_message_id,
                    datetime.now().isoformat()
                ))

                sent_rows.append({
                    "sent_at": sent_at,
                    "to_email": to_email,
                    "to_name": to_name,
                    "subject": subject,
                    "job_title": job["title"],
                    "company": job["company"],
                    "job_link": job["link"],
                    "thread_id": thread_id,
                    "status": "SENT"
                })

        conn.commit()

    return sent_rows
