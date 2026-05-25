from app.sheets_client import get_sheets_service

SHEET_ID = "1DXRX_Q5B9EbryWMyMMHgGfxeOoF8ytu_6KLyMX-z02I"

def main():
    svc = get_sheets_service()

    # Add a Filters tab if not exists
    ss = svc.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    titles = [s["properties"]["title"] for s in ss["sheets"]]
    reqs = []
    if "Filters" not in titles:
        reqs.append({"addSheet": {"properties": {"title": "Filters"}}})

    if reqs:
        svc.spreadsheets().batchUpdate(spreadsheetId=SHEET_ID, body={"requests": reqs}).execute()

    # Filters tab structure (you can add as many rows as you want)
    values = [
        ["filter_name", "include_keywords (comma separated)", "exclude_keywords (comma separated)", "enabled (YES/NO)"],
        ["Python", "python, django, flask, fastapi, pandas", "senior, lead, principal", "YES"],
        ["Data", "data analyst, power bi, tableau, sql, excel", "senior, manager", "YES"],
        ["QA", "qa, tester, automation, selenium, cypress", "senior", "YES"],
        ["DevOps", "devops, aws, azure, docker, kubernetes, ci/cd", "senior", "NO"],
        ["Frontend", "react, next.js, frontend, javascript, typescript", "senior", "NO"],
    ]

    svc.spreadsheets().values().update(
        spreadsheetId=SHEET_ID,
        range="Filters!A1",
        valueInputOption="RAW",
        body={"values": values},
    ).execute()

    print("Filters tab ready ✅")

if __name__ == "__main__":
    main()
