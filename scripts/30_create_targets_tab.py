from app.sheets_client import get_sheets_service

SHEET_ID = "1DXRX_Q5B9EbryWMyMMHgGfxeOoF8ytu_6KLyMX-z02I"

def main():
    svc = get_sheets_service()
    ss = svc.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    titles = [s["properties"]["title"] for s in ss["sheets"]]

    reqs = []
    if "Targets" not in titles:
        reqs.append({"addSheet": {"properties": {"title": "Targets"}}})
    if reqs:
        svc.spreadsheets().batchUpdate(spreadsheetId=SHEET_ID, body={"requests": reqs}).execute()

    values = [
        ["person_id","name","email","department","country","enabled"],
        ["T001","HR Team","hr@example.com","HR","Any","YES"],
    ]

    svc.spreadsheets().values().update(
        spreadsheetId=SHEET_ID,
        range="Targets!A1",
        valueInputOption="RAW",
        body={"values": values}
    ).execute()

    print("Targets tab ready ✅")

if __name__ == "__main__":
    main()
