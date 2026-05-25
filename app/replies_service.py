from datetime import datetime
from pathlib import Path
import pandas as pd

from app.db import get_conn

ROOT = Path(__file__).resolve().parent.parent
EXPORT_DIR = ROOT / "exports"
REPLIES_MASTER = EXPORT_DIR / "replies_master.xlsx"


def _export_replies_master():
    """
    Export replies table to replies_master.xlsx
    """
    with get_conn() as conn:
        df = pd.read_sql_query("""
            SELECT
                r.reply_at,
                r.from_email,
                r.subject,
                r.body_snippet AS snippet,
                r.gmail_thread_id AS thread_id,
                r.outreach_id AS outreach_person_id
            FROM replies r
            ORDER BY r.reply_at DESC
        """, conn)

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    df.to_excel(REPLIES_MASTER, index=False)
    print(f"Replies master updated -> {REPLIES_MASTER} (rows={len(df)})")


def capture_replies_from_threads(svc, max_threads=500):
    captured = 0
    now = datetime.now().isoformat(timespec="seconds")

    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute("""
            SELECT id, gmail_thread_id
            FROM outreach
            WHERE gmail_thread_id IS NOT NULL AND gmail_thread_id != ''
            ORDER BY sent_at DESC
            LIMIT ?
        """, (max_threads,))
        outreach_rows = cur.fetchall()

        for outreach_id, thread_id in outreach_rows:
            t = svc.users().threads().get(
                userId="me",
                id=thread_id,
                format="full"
            ).execute()

            msgs = t.get("messages", [])
            if len(msgs) < 2:
                continue

            last = msgs[-1]
            msg_id = last.get("id")
            body_snippet = (last.get("snippet") or "").strip()[:500]

            headers = {
                h["name"].lower(): h["value"]
                for h in last.get("payload", {}).get("headers", [])
            }

            from_email = (headers.get("from") or "").strip()
            subject = (headers.get("subject") or "").strip()

            # Skip if last message is SENT by me
            label_ids = set(last.get("labelIds", []))
            if "SENT" in label_ids:
                continue

            # Avoid duplicates
            cur.execute("SELECT 1 FROM replies WHERE gmail_message_id=?", (msg_id,))
            if cur.fetchone():
                continue

            # Insert reply
            cur.execute("""
                INSERT INTO replies (
                    outreach_id,
                    reply_at,
                    from_email,
                    subject,
                    body_snippet,
                    gmail_message_id,
                    gmail_thread_id,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                outreach_id,
                now,
                from_email,
                subject,
                body_snippet,
                msg_id,
                thread_id,
                now
            ))

            # Update outreach
            cur.execute("""
                UPDATE outreach
                SET status='REPLIED',
                    last_reply_at=?,
                    last_reply_snippet=?
                WHERE id=?
            """, (now, body_snippet[:250], outreach_id))

            captured += 1

        conn.commit()

    # ✅ Export after capture
    _export_replies_master()

    return captured