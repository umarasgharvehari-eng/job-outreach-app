import re
from app.gmail_client import get_gmail_service
from app.sheets_client import get_sheets_service

SHEET_ID = "1DXRX_Q5B9EbryWMyMMHgGfxeOoF8ytu_6KLyMX-z02I"

HR_KEYWORDS = ["recruit", "talent", "hr", "hiring", "careers", "people ops"]

def main():
    gmail = get_gmail_service()
    sheets = get_sheets_service()

    # Read existing target emails
    existing = sheets.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range="Targets!C2:C5000"
    ).execute().get("values", [])
    existing_emails = set([r[0].strip().lower() for r in existing if r])

    # Search Gmail for likely HR messages
    q = 'newer_than:90d (subject:job OR subject:career OR subject:interview OR subject:application OR subject:recruit)'
    res = gmail.users().messages().list(userId="me", q=q, maxResults=50).execute()
    ids = [m["id"] for m in res.get("messages", [])]

    if not ids:
        print("No emails found.")
        return

    # Pull headers
    msgs = gmail.users().messages().get(userId="me", id=ids[0], format="metadata").execute()

    new_rows = []
    for mid in ids:
        m = gmail.users().messages().get(userId="me", id=mid, format="metadata").execute()
        headers = {h["name"].lower(): h["value"] for h in m.get("payload", {}).get("headers", [])}
        frm = headers.get("from", "")

        # extract email
        match = re.search(r"<([^>]+)>", frm)
        email = (match.group(1) if match else frm).strip().lower()

        if not email or "no-reply" in email:
            continue

        # keyword check
        blob = (headers.get("subject", "") + " " + frm).lower()
        if not any(k in blob for k in HR_KEYWORDS):
            continue

        if email in existing_emails:
            continue

        new_rows.append(["", "Auto HR", email, "HR", "Any", "YES"])
        existing_emails.add(email)

    if not new_rows:
        print("No new HR targets found.")
        return

    sheets.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range="Targets!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": new_rows},
    ).execute()

    print(f"Added HR targets: {len(new_rows)} ✅")

if __name__ == "__main__":
    main()
