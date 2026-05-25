from datetime import datetime
from pathlib import Path

from app.gmail_client import get_gmail_service
from app.gmail_helpers import send_email_with_pdf
from app.db import get_conn
from app.config import FOLLOWUP_DAYS, CV_PDF_PATH
from app.excel_writer import write_daily_xlsx_pro

ROOT = Path(__file__).resolve().parent.parent
EXPORT_DIR = ROOT / "exports"


def main():
    svc = get_gmail_service()
    today = datetime.now().isoformat()

    followup_rows = []
    reply_rows = []

    with get_conn() as conn:
        cur = conn.cursor()

        # 1️⃣ Followups due
        cur.execute("""
            SELECT id, to_email, to_name, subject, gmail_thread_id, followup_due_at
            FROM outreach
            WHERE status='SENT'
        """)
        rows = cur.fetchall()

        for row in rows:
            outreach_id, to_email, to_name, subject, thread_id, due_at = row

            if due_at <= today:
                body = f"""
Hi {to_name},

Just following up on my previous email regarding the application.

Please find my CV attached again.

Thanks,
Umar
"""

                sent_message_id, new_thread_id = send_email_with_pdf(
                    svc,
                    to_email=to_email,
                    subject="Follow-up: " + subject,
                    body_text=body,
                    pdf_path=CV_PDF_PATH,
                    thread_id=thread_id
                )

                cur.execute("""
                    UPDATE outreach
                    SET status='FOLLOWUP_SENT',
                        followup_sent_at=?
                    WHERE id=?
                """, (today, outreach_id))

                followup_rows.append({
                    "to_email": to_email,
                    "subject": subject,
                    "followup_sent_at": today,
                    "status": "FOLLOWUP_SENT"
                })

        # 2️⃣ Check replies
        cur.execute("""
            SELECT id, gmail_thread_id
            FROM outreach
            WHERE gmail_thread_id IS NOT NULL
        """)
        outreach_rows = cur.fetchall()

        for outreach_id, thread_id in outreach_rows:
            thread = svc.users().threads().get(userId="me", id=thread_id).execute()
            messages = thread.get("messages", [])

            for msg in messages:
                headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
                from_email = headers.get("From", "")

                if "umarasgharvehari" not in from_email.lower():
                    reply_rows.append({
                        "outreach_id": outreach_id,
                        "from_email": from_email,
                        "subject": headers.get("Subject", ""),
                        "reply_at": datetime.fromtimestamp(int(msg["internalDate"]) / 1000).isoformat()
                    })

                    cur.execute("""
                        UPDATE outreach
                        SET status='REPLIED'
                        WHERE id=?
                    """, (outreach_id,))

        conn.commit()

    # Export followups
    if followup_rows:
        out1 = EXPORT_DIR / f"followups_{datetime.now().date().isoformat()}.xlsx"
        write_daily_xlsx_pro(
            out1,
            followup_rows,
            ["to_email","subject","followup_sent_at","status"],
            sheet_name="Followups",
            date_cols=["followup_sent_at"],
        )
        print(f"Followups exported -> {out1}")

    # Export replies
    if reply_rows:
        out2 = EXPORT_DIR / f"replies_{datetime.now().date().isoformat()}.xlsx"
        write_daily_xlsx_pro(
            out2,
            reply_rows,
            ["outreach_id","from_email","subject","reply_at"],
            sheet_name="Replies",
            date_cols=["reply_at"],
        )
        print(f"Replies exported -> {out2}")

    print("Follow-up & reply check complete.")


if __name__ == "__main__":
    main()
