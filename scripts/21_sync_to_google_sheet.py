from datetime import datetime
from app.sheets_client import get_sheets_service
from app.db import get_conn, init_db

SHEET_ID = "1DXRX_Q5B9EbryWMyMMHgGfxeOoF8ytu_6KLyMX-z02I"


def clear_and_write(service, tab, headers, rows):
    service.spreadsheets().values().clear(
        spreadsheetId=SHEET_ID,
        range=f"{tab}!A:Z",
        body={}
    ).execute()

    values = [headers] + rows

    service.spreadsheets().values().update(
        spreadsheetId=SHEET_ID,
        range=f"{tab}!A1",
        valueInputOption="RAW",
        body={"values": values}
    ).execute()


def read_filters(service):
    res = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range="Filters!A2:D200"
    ).execute()

    rows = res.get("values", [])
    filters = []

    for r in rows:
        if len(r) < 4:
            continue

        name = r[0].strip()
        include = [x.strip().lower() for x in r[1].split(",") if x.strip()]
        exclude = [x.strip().lower() for x in r[2].split(",") if x.strip()]
        enabled = r[3].strip().upper() == "YES"

        if enabled and include:
            filters.append((name, include, exclude))

    return filters


def match_job(text, filters):
    text = (text or "").lower()
    matched = []

    for name, include, exclude in filters:
        if any(e in text for e in exclude):
            continue
        if any(k in text for k in include):
            matched.append(name)

    if matched:
        return "YES", ", ".join(matched)

    return "NO", ""


def main():
    init_db()
    service = get_sheets_service()
    filters = read_filters(service)

    conn = get_conn()
    cur = conn.cursor()

    # ---------------- JOBS ----------------
    cur.execute("""
        SELECT received_at, source, title, company, location, link, from_email, subject
        FROM jobs
        ORDER BY received_at DESC
        LIMIT 2000
    """)

    jobs_data = cur.fetchall()
    jobs_rows = []

    for row in jobs_data:
        received_at, source, title, company, location, link, from_email, subject = row
        text_blob = f"{title} {company} {location} {subject}"

        match_flag, matched_filters = match_job(text_blob, filters)

        jobs_rows.append([
            received_at,
            source,
            title,
            company,
            location,
            link,
            from_email,
            subject,
            match_flag,
            matched_filters
        ])

    clear_and_write(
        service,
        "Jobs",
        ["received_at","source","title","company","location","link","from_email","subject","match","matched_filters"],
        jobs_rows
    )

    # ---------------- OUTREACH ----------------
    cur.execute("""
        SELECT sent_at, to_email, to_name, subject, status, followup_due_at, followup_sent_at, gmail_thread_id
        FROM outreach
        ORDER BY sent_at DESC
        LIMIT 2000
    """)

    outreach_rows = [list(r) for r in cur.fetchall()]

    clear_and_write(
        service,
        "Outreach",
        ["sent_at","to_email","to_name","subject","status","followup_due_at","followup_sent_at","thread_id"],
        outreach_rows
    )

    # ---------------- REPLIES ----------------
    cur.execute("""
        SELECT reply_at, from_email, subject, body_snippet, gmail_thread_id, outreach_id
        FROM replies
        ORDER BY reply_at DESC
        LIMIT 2000
    """)

    replies_rows = [list(r) for r in cur.fetchall()]

    clear_and_write(
        service,
        "Replies",
        ["reply_at","from_email","subject","snippet","thread_id","outreach_id"],
        replies_rows
    )

    conn.close()

    # ---------------- DASHBOARD ----------------
    dashboard_rows = [
        ["Last Sync", datetime.now().isoformat(timespec="seconds")],
        ["Total Jobs", "=COUNTA(Jobs!A2:A)"],
        ["Total Emails Sent", "=COUNTA(Outreach!A2:A)"],
        ["SENT", '=COUNTIF(Outreach!E2:E,"SENT")'],
        ["FOLLOWUP_SENT", '=COUNTIF(Outreach!E2:E,"FOLLOWUP_SENT")'],
        ["REPLIED", '=COUNTIF(Outreach!E2:E,"REPLIED")'],
        ["Replies Received", "=COUNTA(Replies!A2:A)"],
        ["Response Rate", "=IFERROR(COUNTA(Replies!A2:A)/COUNTA(Outreach!A2:A),0)"],
    ]

    clear_and_write(service, "Dashboard", ["Metric","Value"], dashboard_rows)

    print("Synced to Google Sheet with Filters ✅")


if __name__ == "__main__":
    main()
