from datetime import datetime
from pathlib import Path

from app.gmail_client import get_gmail_service
from app.gmail_helpers import extract_headers, get_message_body
from app.parsers import parse_job
from app.db import get_conn, init_db
from app.excel_writer import write_daily_xlsx_pro

EXPORT_DIR = Path(__file__).resolve().parent.parent / "exports"

def main():
    init_db()
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    svc = get_gmail_service()

    # ✅ tighter query: only likely job sources (still safe)
    q = (
        "newer_than:30d ("
        "from:linkedin OR from:indeed OR from:freelancer OR from:glassdoor OR "
        "from:ziprecruiter OR subject:(job OR jobs OR hiring OR career OR vacancy OR opening)"
        ")"
        " -subject:(otp OR login OR transaction OR debit OR credit OR netflix OR invoice OR receipt OR payment)"
    )

    rows = []
    inserted = 0
    skipped_non_jobs = 0

    # pagination to get more than 50 if needed
    page_token = None

    with get_conn() as conn:
        cur = conn.cursor()

        while True:
            res = svc.users().messages().list(
                userId="me",
                q=q,
                maxResults=100,
                pageToken=page_token
            ).execute()

            msgs = res.get("messages", [])
            if not msgs:
                break

            for m in msgs:
                msg = svc.users().messages().get(
                    userId="me",
                    id=m["id"],
                    format="full"
                ).execute()

                headers = extract_headers(msg["payload"])
                subject = headers.get("subject", "") or ""
                from_email = headers.get("from", "") or ""
                body = get_message_body(msg["payload"])

                # ✅ IMPORTANT: pass from_email to parser
               job = parse_job(subject, body, from_email=from_email)
                if not job.get("is_job"):
                skipped_non_jobs += 1
                continue


                received_at = datetime.fromtimestamp(
                    int(msg["internalDate"]) / 1000
                ).isoformat()

                created_at = datetime.now().isoformat()

                cur.execute("""
                    INSERT OR IGNORE INTO jobs
                    (source, received_at, subject, title, company, location, link, description, from_email, gmail_message_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.get("source") or "JobAlert",
                    received_at,
                    subject,
                    job.get("title"),
                    job.get("company"),
                    job.get("location"),
                    job.get("link"),
                    job.get("description"),
                    from_email,
                    msg["id"],
                    created_at
                ))

                if cur.rowcount == 1:
                    inserted += 1

                rows.append({
                    "received_at": received_at,
                    "source": job.get("source") or "JobAlert",
                    "title": job.get("title"),
                    "company": job.get("company"),
                    "location": job.get("location"),
                    "link": job.get("link"),
                    "from_email": from_email,
                    "subject": subject
                })

            conn.commit()

            page_token = res.get("nextPageToken")
            if not page_token:
                break

    today = datetime.now().date().isoformat()
    out = EXPORT_DIR / f"jobs_{today}.xlsx"

    COLUMNS = [
        "received_at",
        "source",
        "title",
        "company",
        "location",
        "link",
        "from_email",
        "subject",
    ]

    write_daily_xlsx_pro(
        out,
        rows=rows,
        columns=COLUMNS,
        sheet_name="Jobs",
        date_cols=["received_at"],
        hyperlink_cols=["link"],
    )

    print(f"Saved {len(rows)} jobs -> {out} | inserted={inserted} | skipped_non_jobs={skipped_non_jobs}")

if __name__ == "__main__":
    main()
