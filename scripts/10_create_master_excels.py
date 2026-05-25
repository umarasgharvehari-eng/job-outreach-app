from pathlib import Path
from datetime import datetime
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parent.parent
EXPORTS = ROOT / "exports"

def make_wb(path: Path, sheet: str, headers: list[str]):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(headers)
    wb.save(path)

def main():
    EXPORTS.mkdir(parents=True, exist_ok=True)

    outreach_path = EXPORTS / "outreach_master.xlsx"
    jobs_path = EXPORTS / "jobs_master.xlsx"
    replies_path = EXPORTS / "replies_master.xlsx"

    if not outreach_path.exists():
        make_wb(outreach_path, "Outreach", [
            "person_id","to_email","to_name","job_title","company","job_link",
            "message_template","send_flag","status","batch_id",
            "sent_at","followup_due_at","thread_id",
            "last_reply_at","last_reply_snippet"
        ])

    if not jobs_path.exists():
        make_wb(jobs_path, "Jobs", [
            "received_at","source","title","company","location","link","description","email_id"
        ])

    if not replies_path.exists():
        make_wb(replies_path, "Replies", [
            "reply_at","from_email","subject","snippet","thread_id","outreach_person_id"
        ])

    print("Master Excel files ready in exports/")

if __name__ == "__main__":
    main()
