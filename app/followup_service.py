from datetime import datetime
from app.db import get_conn
from app.gmail_helpers import send_followup_in_thread
from app.config import FOLLOWUP_TEMPLATE


def run_followups(svc, limit=20):
    """
    Sends followups for rows where:
    - status = SENT
    - followup_sent_at is NULL
    - followup_due_at <= now
    """
    now = datetime.now().isoformat(timespec="seconds")
    sent = 0

    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute("""
            SELECT id, to_email, to_name, subject, gmail_thread_id
            FROM outreach
            WHERE status='SENT'
              AND (followup_sent_at IS NULL OR followup_sent_at='')
              AND followup_due_at IS NOT NULL
              AND followup_due_at <= ?
            ORDER BY followup_due_at ASC
            LIMIT ?
        """, (now, limit))

        rows = cur.fetchall()

        for outreach_id, to_email, to_name, subject, thread_id in rows:
            if not thread_id:
                continue

            body = FOLLOWUP_TEMPLATE.format(name=to_name or "there")

            # Send followup inside same thread
            send_followup_in_thread(
                svc,
                to_email=to_email,
                subject="Re: " + (subject or ""),
                body_text=body,
                thread_id=thread_id
            )

            cur.execute("""
                UPDATE outreach
                SET status='FOLLOWUP_SENT',
                    followup_sent_at=?
                WHERE id=?
            """, (now, outreach_id))

            sent += 1

        conn.commit()

    return sent
