from app.sheets_client import get_sheets_service

SHEET_ID = "1DXRX_Q5B9EbryWMyMMHgGfxeOoF8ytu_6KLyMX-z02I"

def main():
    svc = get_sheets_service()

    # Add Settings sheet if not exists
    spreadsheet = svc.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    existing = [s["properties"]["title"] for s in spreadsheet["sheets"]]

    if "Settings" not in existing:
        svc.spreadsheets().batchUpdate(
            spreadsheetId=SHEET_ID,
            body={
                "requests": [
                    {"addSheet": {"properties": {"title": "Settings"}}}
                ]
            }
        ).execute()

    values = [
        ["Setting", "Value"],
        ["max_emails_per_day", "50"],
        ["batch_size", "10"],
        ["batch_interval_minutes", "15"],
        ["followup_days", "7"],
        ["daily_start_hour", "9"],
        ["daily_end_hour", "18"]
    ]

    svc.spreadsheets().values().update(
        spreadsheetId=SHEET_ID,
        range="Settings!A1",
        valueInputOption="RAW",
        body={"values": values}
    ).execute()

    print("Settings tab ready ✅")

if __name__ == "__main__":
    main()
