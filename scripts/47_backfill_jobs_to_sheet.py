# scripts/47_backfill_jobs_to_sheet.py
# Backfill Jobs tab in Google Sheet directly from SQLite jobs table

import sqlite3
from datetime import datetime, timedelta

from app.sheets_client import get_sheets_service

SHEET_ID = "1DXRX_Q5B9EbryWMyMMHgGfxeOoF8ytu_6KLyMX-z02I"
TAB_NAME = "Jobs"
DB_PATH = "data/bot.db"

HEADERS = [
    "received_at", "source", "title", "company", "location",
    "link", "from_email", "subject", "match", "matched_filters"
]

def main(days_back: int = 14, overwrite: bool = True):
    start_dt = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # match/matched_filters might not be in DB jobs table; we'll fill blanks
    rows = cur.execute("""
        SELECT received_at, source, title, company, location, link, from_email, subject
        FROM jobs
        WHERE received_at >= ?
        ORDER BY received_at DESC
    """, (start_dt,)).fetchall()
    conn.close()

    values = [HEADERS]
    for r in rows:
        received_at, source, title, company, location, link, from_email, subject = r
        values.append([
            received_at or "",
            source or "",
            title or "",
            company or "",
            location or "",
            link or "",
            from_email or "",
            subject or "",
            "",   # match
            ""    # matched_filters
        ])

    svc = get_sheets_service()

    if overwrite:
        # Clear existing Jobs tab range then write fresh
        svc.spreadsheets().values().clear(
            spreadsheetId=SHEET_ID,
            range=f"{TAB_NAME}!A:Z"
        ).execute()

        svc.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=f"{TAB_NAME}!A1",
            valueInputOption="RAW",
            body={"values": values}
        ).execute()
        print(f"✅ Backfilled {len(rows)} jobs into Google Sheet (OVERWRITE) from {start_dt}")
    else:
        # Append mode
        svc.spreadsheets().values().append(
            spreadsheetId=SHEET_ID,
            range=f"{TAB_NAME}!A1",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": values[1:]}  # no header
        ).execute()
        print(f"✅ Appended {len(rows)} jobs into Google Sheet from {start_dt}")

if __name__ == "__main__":
    main(days_back=30, overwrite=True)
