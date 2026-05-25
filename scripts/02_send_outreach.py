from datetime import datetime
from pathlib import Path

from app.gmail_client import get_gmail_service
from app.excel_writer import write_daily_xlsx_pro
from app.db import init_db
from app.outreach_service import send_for_latest_jobs

ROOT = Path(__file__).resolve().parent.parent
EXPORT_DIR = ROOT / "exports"
RECIPIENTS_CSV = ROOT / "data" / "recipients.csv"
TEMPLATE_PATH = ROOT / "templates" / "first_email.txt"

def main():
    init_db()
    svc = get_gmail_service()

    sent_rows = send_for_latest_jobs(
        svc,
        recipients_csv=RECIPIENTS_CSV,
        template_path=TEMPLATE_PATH,
        max_jobs=2,          # start small for testing
        max_recipients=2     # start small for testing
    )

    today = datetime.now().date().isoformat()
    out = EXPORT_DIR / f"outreach_{today}.xlsx"

    cols = ["sent_at","to_email","to_name","subject","job_title","company","job_link","thread_id","status"]
    write_daily_xlsx_pro(
        out,
        rows=sent_rows,
        columns=cols,
        sheet_name="Outreach",
        date_cols=["sent_at"],
        hyperlink_cols=["job_link"],
    )

    print(f"Sent {len(sent_rows)} emails -> {out}")

if __name__ == "__main__":
    main()
