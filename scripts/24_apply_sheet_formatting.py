from app.sheets_client import get_sheets_service

SHEET_ID = "1DXRX_Q5B9EbryWMyMMHgGfxeOoF8ytu_6KLyMX-z02I"

def get_sheet_id(service, title: str) -> int:
    ss = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    for s in ss["sheets"]:
        if s["properties"]["title"] == title:
            return s["properties"]["sheetId"]
    raise ValueError(f"Sheet not found: {title}")

def main():
    svc = get_sheets_service()
    outreach_sheet_id = get_sheet_id(svc, "Outreach")

    # Apply conditional formatting on column E (status) from row 2
    requests = []

    def add_rule(text, red=None, green=None, blue=None):
        return {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": outreach_sheet_id,
                        "startRowIndex": 1,   # row 2
                        "startColumnIndex": 4, # col E (0-based)
                        "endColumnIndex": 5
                    }],
                    "booleanRule": {
                        "condition": {
                            "type": "TEXT_EQ",
                            "values": [{"userEnteredValue": text}]
                        },
                        "format": {
                            "backgroundColor": {
                                "red": red or 0,
                                "green": green or 0,
                                "blue": blue or 0
                            }
                        }
                    }
                },
                "index": 0
            }
        }

    # Colors (0..1 floats)
    requests.append(add_rule("SENT", red=0.80, green=0.95, blue=0.80))
    requests.append(add_rule("FOLLOWUP_SENT", red=0.95, green=0.93, blue=0.75))
    requests.append(add_rule("REPLIED", red=0.80, green=0.88, blue=0.98))
    requests.append(add_rule("STOP", red=0.98, green=0.80, blue=0.80))

    svc.spreadsheets().batchUpdate(
        spreadsheetId=SHEET_ID,
        body={"requests": requests}
    ).execute()

    print("Conditional formatting applied ✅")

if __name__ == "__main__":
    main()
