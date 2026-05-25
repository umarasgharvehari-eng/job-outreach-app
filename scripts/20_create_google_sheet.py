from app.sheets_client import get_sheets_service

def main():
    svc = get_sheets_service()

    spreadsheet = svc.spreadsheets().create(body={
        "properties": {"title": "Job Outreach Dashboard"},
        "sheets": [
            {"properties": {"title": "Jobs"}},
            {"properties": {"title": "Outreach"}},
            {"properties": {"title": "Replies"}},
            {"properties": {"title": "Dashboard"}},
        ]
    }).execute()

    print("Spreadsheet ID:", spreadsheet["spreadsheetId"])
    print("Open it in browser (copy ID and open): https://docs.google.com/spreadsheets/d/" + spreadsheet["spreadsheetId"])

if __name__ == "__main__":
    main()
