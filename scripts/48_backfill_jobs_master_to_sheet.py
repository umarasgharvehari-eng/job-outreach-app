# scripts/48_backfill_jobs_master_to_sheet.py
# Backfill Google Sheet Jobs tab from exports/jobs_master.xlsx (NOT from SQLite)

from datetime import datetime, timedelta
import pandas as pd
from app.sheets_client import get_sheets_service

SHEET_ID = "1DXRX_Q5B9EbryWMyMMHgGfxeOoF8ytu_6KLyMX-z02I"
TAB_NAME = "Jobs"
MASTER_XLSX = "exports/jobs_master.xlsx"

HEADERS = [
    "received_at", "source", "title", "company", "location",
    "link", "from_email", "subject", "match", "matched_filters"
]

def main(days_back: int = 30, overwrite: bool = True):
    df = pd.read_excel(MASTER_XLSX)

    # ensure all needed cols exist
    for col in ["received_at","source","title","company","location","link","from_email","subject"]:
        if col not in df.columns:
            df[col] = ""

    # normalize datetime to string
    df["received_at"] = df["received_at"].astype(str)

    start_dt = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    df = df[df["received_at"] >= start_dt].copy()

    # newest first
    df = df.sort_values("received_at", ascending=False)

    # Build values for sheet
    values = [HEADERS]
    for _, r in df.iterrows():
        values.append([
            str(r.get("received_at","") or ""),
            str(r.get("source","") or ""),
            str(r.get("title","") or ""),
            str(r.get("company","") or ""),
            str(r.get("location","") or ""),
            str(r.get("link","") or ""),
            str(r.get("from_email","") or ""),
            str(r.get("subject","") or ""),
            "",  # match
            ""   # matched_filters
        ])

    svc = get_sheets_service()

    if overwrite:
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
        print(f"✅ Backfilled {len(values)-1} jobs into Google Sheet from MASTER (OVERWRITE) starting {start_dt}")
    else:
        svc.spreadsheets().values().append(
            spreadsheetId=SHEET_ID,
            range=f"{TAB_NAME}!A1",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": values[1:]}
        ).execute()
        print(f"✅ Appended {len(values)-1} jobs into Google Sheet from MASTER starting {start_dt}")

if __name__ == "__main__":
    main(days_back=60, overwrite=True)
