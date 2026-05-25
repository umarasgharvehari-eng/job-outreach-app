from datetime import datetime
from pathlib import Path

from app.gmail_client import get_gmail_service
from app.db import init_db
from app.excel_outreach import send_from_outreach_master
from app.sheet_settings import load_settings

ROOT = Path(__file__).resolve().parent.parent
OUTREACH_MASTER = ROOT / "exports" / "outreach_master.xlsx"


def main():
    init_db()

    settings = load_settings()
    now = datetime.now()

    # ✅ Sending window control (e.g. 9 to 18)
    start_h = settings.get("daily_start_hour", 9)
    end_h = settings.get("daily_end_hour", 18)

    if now.hour < start_h or now.hour > end_h:
        print(f"Outside sending window ({start_h}:00–{end_h}:00). Skipping.")
        return

    svc = get_gmail_service()

    batch_size = settings.get("batch_size", 10)

    sent = send_from_outreach_master(
        svc,
        outreach_path=OUTREACH_MASTER,
        max_per_run=batch_size,
    )

    print(f"Sent this run: {sent}")


if __name__ == "__main__":
    main()
