from app.sheets_client import get_sheets_service

SHEET_ID = "1DXRX_Q5B9EbryWMyMMHgGfxeOoF8ytu_6KLyMX-z02I"

def load_settings():
    svc = get_sheets_service()

    res = svc.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range="Settings!A2:B20"
    ).execute()

    rows = res.get("values", [])

    settings = {}
    for r in rows:
        if len(r) >= 2:
            settings[r[0]] = r[1]

    return {
        "max_emails_per_day": int(settings.get("max_emails_per_day", 50)),
        "batch_size": int(settings.get("batch_size", 10)),
        "batch_interval_minutes": int(settings.get("batch_interval_minutes", 15)),
        "followup_days": int(settings.get("followup_days", 7)),
        "daily_start_hour": int(settings.get("daily_start_hour", 9)),
        "daily_end_hour": int(settings.get("daily_end_hour", 18)),
        "followup_hour": int(settings.get("followup_hour", 11)),
        "followup_minute": int(settings.get("followup_minute", 0)),
    }
