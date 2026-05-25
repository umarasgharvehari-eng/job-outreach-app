from pathlib import Path
import pandas as pd
from app.sheets_client import get_sheets_service

SHEET_ID = "1DXRX_Q5B9EbryWMyMMHgGfxeOoF8ytu_6KLyMX-z02I"

ROOT = Path(__file__).resolve().parent.parent
JOBS_MASTER = ROOT / "jobs_master.xlsx"

def clear_and_write(svc, tab, values):
    # clear whole tab
    svc.spreadsheets().values().clear(
        spreadsheetId=SHEET_ID,
        range=f"{tab}!A:Z",
        body={}
    ).execute()

    # write fresh
    svc.spreadsheets().values().update(
        spreadsheetId=SHEET_ID,
        range=f"{tab}!A1",
        valueInputOption="RAW",
        body={"values": values}
    ).execute()

def main():
    svc = get_sheets_service()

    df = pd.read_excel(JOBS_MASTER, sheet_name="Jobs")

    # ✅ ensure column exists even if empty
    if "contact_email" not in df.columns:
        df["contact_email"] = ""

    # keep order nice
    wanted = [
        "received_at","source","title","company","location",
        "link","description","email_id","contact_email"
    ]
    cols = [c for c in wanted if c in df.columns] + [c for c in df.columns if c not in wanted]
    df = df[cols]

    # convert to values
    values = [df.columns.tolist()] + df.fillna("").astype(str).values.tolist()

    clear_and_write(svc, "Jobs", values)
    print(f"Jobs synced to sheet ✅ rows={len(df)} cols={len(df.columns)}")

if __name__ == "__main__":
    main()