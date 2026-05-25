# scripts/46_sync_last_days_to_sheet.py
from datetime import datetime, timedelta
import sqlite3

from app.sheets_sync import sync_jobs_to_sheet  # agar tumhare project me ye function hai
# agar function ka naam different ho to mujhe file ka naam bata dena

DB = "data/bot.db"

def main(days_back=3):
    start = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT received_at, source, title, company, location, link, from_email, subject "
        "FROM jobs WHERE received_at >= ? ORDER BY received_at ASC",
        (start,)
    ).fetchall()
    conn.close()

    print("Rows to backfill:", len(rows))
    sync_jobs_to_sheet(rows)  # yahan tumhari existing sheet sync call use hogi
    print("Backfill done ✅")

if __name__ == "__main__":
    main(3)
