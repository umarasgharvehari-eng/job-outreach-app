import sqlite3
from app.sheets_client import get_sheets_service

SHEET_ID = "1DXRX_Q5B9EbryWMyMMHgGfxeOoF8ytu_6KLyMX-z02I"
DB_PATH = "data/bot.db"

def main():
    sheets = get_sheets_service()

    # Read sheet rows
    resp = sheets.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range="Outreach!A1:H5000"
    ).execute()
    values = resp.get("values", [])
    if not values or len(values) < 2:
        print("No sheet outreach rows found.")
        return

    header = values[0]
    rows = values[1:]

    idx = {h.strip(): i for i, h in enumerate(header)}
    required = ["sent_at","to_email","subject","status","followup_due_at","followup_sent_at","thread_id"]
    for k in required:
        if k not in idx:
            print("Missing column in sheet:", k, "Header:", header)
            return

    # Build map: (email, subject) -> row_index_in_sheet (1-based in A1 notation)
    sheet_map = {}
    for i, r in enumerate(rows, start=2):  # row number in sheet
        email = (r[idx["to_email"]] if idx["to_email"] < len(r) else "").strip().lower()
        subject = (r[idx["subject"]] if idx["subject"] < len(r) else "").strip()
        if email and subject:
            sheet_map[(email, subject)] = i

    # Read DB outreach
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT to_email, subject, status, sent_at, followup_due_at, followup_sent_at, gmail_thread_id
        FROM outreach
        ORDER BY sent_at DESC
        LIMIT 2000
    """)
    db_rows = cur.fetchall()
    conn.close()

    updates = []
    for to_email, subject, status, sent_at, due_at, fu_sent_at, thread_id in db_rows:
        key = (str(to_email).strip().lower(), str(subject).strip())
        rownum = sheet_map.get(key)
        if not rownum:
            continue

        # Prepare row H values (A-H)
        # We only update the cells we manage: A, E, F, G, H
        # A sent_at
        # E status
        # F followup_due_at
        # G followup_sent_at
        # H thread_id
        updates.append({
            "range": f"Outreach!A{rownum}:H{rownum}",
            "values": [[
                sent_at or "",
                to_email or "",
                "",  # to_name untouched (keep whatever is there) -> we'll preserve below
                subject or "",
                status or "",
                due_at or "",
                fu_sent_at or "",
                thread_id or "",
            ]]
        })

    if not updates:
        print("No matching rows to update.")
        return

    # IMPORTANT: preserve existing to_name (col C)
    # We'll read current row and only replace managed columns.
    # For simplicity: update full row but keep to_name from sheet.
    batch_data = []
    for u in updates:
        r = u["range"]
        # read current row to keep to_name
        cur_row = sheets.spreadsheets().values().get(
            spreadsheetId=SHEET_ID, range=r
        ).execute().get("values", [[]])[0]

        new_row = u["values"][0]
        # keep to_name (C index 2)
        if len(cur_row) >= 3 and cur_row[2]:
            new_row[2] = cur_row[2]
        batch_data.append({"range": r, "values": [new_row]})

    sheets.spreadsheets().values().batchUpdate(
        spreadsheetId=SHEET_ID,
        body={"valueInputOption": "RAW", "data": batch_data}
    ).execute()

    print(f"Synced {len(batch_data)} outreach rows back to sheet ✅")

if __name__ == "__main__":
    main()
