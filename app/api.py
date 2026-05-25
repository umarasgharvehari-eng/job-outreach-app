import base64
import json
import mimetypes
import subprocess
import sys
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parent.parent
EXPORTS = ROOT / "exports"
STATE = ROOT / "services" / "state.json"
LOGF = ROOT / "services" / "worker.log"
RESUME = ROOT / "attachments" / "resume.pdf"
TOKEN = ROOT / "token.json"

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/spreadsheets",
]

app = FastAPI(title="Job Outreach API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://taupe-raindrop-4ccd70.netlify.app",
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


def now():
    return datetime.now().isoformat(timespec="seconds")


def read_state() -> dict:
    if not STATE.exists():
        return {}
    try:
        txt = STATE.read_text(encoding="utf-8").strip()
        return json.loads(txt) if txt else {}
    except Exception:
        return {}


def write_state(**kwargs):
    data = read_state()
    data.update(kwargs)
    data["updated_at"] = now()
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(data, indent=2), encoding="utf-8")


@app.on_event("startup")
def auto_start_worker_on_api_start():
    state = read_state()

    if state.get("running") is True:
        return

    write_state(
        running=True,
        last_job="auto_worker_start",
        last_job_at=now(),
    )

    subprocess.Popen(
        [sys.executable, "services/worker.py"],
        cwd=str(ROOT),
    )


@app.get("/")
def root():
    return {"app": "Job Outreach API", "status": "running", "docs": "/docs"}


def first_existing(*paths: Path):
    for path in paths:
        if path and path.exists():
            return path
    return None


def load_excel_any(path: Path | None):
    if not path:
        return pd.DataFrame()

    try:
        xls = pd.ExcelFile(path)
        frames = []

        for sheet in xls.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet)
            df["__sheet"] = sheet
            frames.append(df)

        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def find_col(df: pd.DataFrame, candidates: list[str]):
    if df.empty:
        return None

    cols = {str(c).lower().strip(): c for c in df.columns}

    for candidate in candidates:
        if candidate.lower() in cols:
            return cols[candidate.lower()]

    for col in df.columns:
        col_lower = str(col).lower()
        for candidate in candidates:
            if candidate.lower() in col_lower:
                return col

    return None


def contains_any(series: pd.Series, keywords: list[str]):
    text = series.fillna("").astype(str).str.lower()
    pattern = "|".join(keywords)
    return text.str.contains(pattern, na=False, regex=True)


def df_to_records(df: pd.DataFrame, limit: int = 100):
    if df.empty:
        return []

    df = df.fillna("")
    records = df.head(limit).to_dict(orient="records")

    clean = []
    for row in records:
        clean.append({str(k): str(v) for k, v in row.items()})

    return clean


def get_gmail_send_service():
    if not TOKEN.exists():
        raise FileNotFoundError("token.json not found. Run inbox sync once and authorize Gmail.")

    creds = Credentials.from_authorized_user_file(str(TOKEN), scopes=GMAIL_SCOPES)
    return build("gmail", "v1", credentials=creds)


def send_email(to_email: str, subject: str, body: str, attach_resume: bool = True):
    service = get_gmail_send_service()

    msg = EmailMessage()
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    if attach_resume:
        if not RESUME.exists():
            raise FileNotFoundError(f"Resume not found: {RESUME}")

        mime_type, _ = mimetypes.guess_type(str(RESUME))
        if not mime_type:
            mime_type = "application/pdf"

        maintype, subtype = mime_type.split("/", 1)

        with open(RESUME, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype=maintype,
                subtype=subtype,
                filename="resume.pdf",
            )

    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    return service.users().messages().send(
        userId="me",
        body={"raw": raw_message},
    ).execute()


@app.get("/api/state")
def get_state():
    from app.supabase_db import supabase
    response = supabase.table("jobs").select("*").limit(1).execute()
    return {"success": True, "data": response.data}


@app.post("/api/worker/start")
def start_worker():
    write_state(running=True)

    subprocess.Popen(
        [sys.executable, "services/worker.py"],
        cwd=str(ROOT),
    )

    return {"success": True, "message": "Worker started"}


@app.post("/api/worker/stop")
def stop_worker():
    write_state(running=False)
    return {"success": True, "message": "Worker stop requested"}


@app.post("/api/jobs/inbox-sync")
def run_inbox_sync():
    subprocess.Popen(
        [sys.executable, "-m", "scripts.45_run_inbox_fast"],
        cwd=str(ROOT),
    )

    write_state(
        last_job="inbox_sync",
        last_job_at=now(),
    )

    return {"success": True, "message": "Inbox sync started"}


@app.post("/api/jobs/sync-latest")
def sync_latest_jobs():
    subprocess.Popen(
        [sys.executable, "-m", "scripts.45_run_inbox_fast"],
        cwd=str(ROOT),
    )

    write_state(
        last_job="sync_latest_jobs",
        last_job_at=now(),
    )

    return {"success": True, "message": "Latest job sync started"}


@app.get("/api/logs")
def get_logs(limit: int = 200):
    if not LOGF.exists():
        return {"logs": []}

    lines = LOGF.read_text(encoding="utf-8").splitlines()[-limit:]
    return {"logs": lines}


@app.get("/api/dashboard/summary")
def dashboard_summary():
    jobs_path = first_existing(ROOT / "jobs_master.xlsx", EXPORTS / "jobs_master.xlsx")
    outreach_path = first_existing(ROOT / "outreach_master.xlsx", EXPORTS / "outreach_master.xlsx")
    replies_path = first_existing(ROOT / "replies_master.xlsx", EXPORTS / "replies_master.xlsx")

    jobs_df = load_excel_any(jobs_path)
    outreach_df = load_excel_any(outreach_path)
    replies_df = load_excel_any(replies_path)

    location_col = find_col(jobs_df, ["location", "country", "city"])
    followup_col = find_col(
        outreach_df,
        ["followup", "follow_up", "follow up", "followup_status", "follow_up_status"],
    )

    total_jobs = len(jobs_df)
    applied_jobs = len(outreach_df)
    total_replies = len(replies_df)

    uk_jobs = 0
    if location_col:
        uk_jobs = int(
            contains_any(
                jobs_df[location_col],
                ["uk", "united kingdom", "london", "manchester", "birmingham", "england"],
            ).sum()
        )

    pending_followups = 0
    followups_sent = 0

    if followup_col:
        followups = outreach_df[followup_col]
        pending_followups = int(
            contains_any(followups, ["pending", "due", "needed", "not sent", "todo"]).sum()
        )
        followups_sent = int(
            contains_any(followups, ["sent", "done", "completed"]).sum()
        )

    return {
        "totalJobsFound": total_jobs,
        "appliedJobs": applied_jobs,
        "ukJobs": uk_jobs,
        "totalReplies": total_replies,
        "pendingFollowups": pending_followups,
        "followupsSent": followups_sent,
        "newJobsNotEmailed": max(total_jobs - applied_jobs, 0),
    }


@app.get("/api/jobs/new")
def get_new_jobs(limit: int = 100):
    jobs_path = first_existing(ROOT / "jobs_master.xlsx", EXPORTS / "jobs_master.xlsx")
    outreach_path = first_existing(ROOT / "outreach_master.xlsx", EXPORTS / "outreach_master.xlsx")

    jobs_df = load_excel_any(jobs_path)
    outreach_df = load_excel_any(outreach_path)

    if jobs_df.empty:
        return {"jobs": []}

    date_col = find_col(jobs_df, ["received_at", "created_at", "date", "posted_at", "timestamp"])

    if date_col:
        jobs_df["_sort_date"] = pd.to_datetime(jobs_df[date_col], errors="coerce")
        jobs_df = jobs_df.sort_values("_sort_date", ascending=False)

    job_id_col = find_col(jobs_df, ["job_id", "id", "url", "link"])
    outreach_id_col = find_col(outreach_df, ["job_id", "id", "url", "link"])

    if job_id_col and outreach_id_col and not outreach_df.empty:
        applied_ids = set(
            outreach_df[outreach_id_col]
            .fillna("")
            .astype(str)
            .str.lower()
            .str.strip()
            .tolist()
        )

        jobs_df = jobs_df[
            ~jobs_df[job_id_col]
            .fillna("")
            .astype(str)
            .str.lower()
            .str.strip()
            .isin(applied_ids)
        ]

    if "_sort_date" in jobs_df.columns:
        jobs_df = jobs_df.drop(columns=["_sort_date"])

    return {"jobs": df_to_records(jobs_df, limit)}


@app.post("/api/jobs/apply")
def apply_jobs(payload: dict):
    jobs = payload.get("jobs", [])
    message = payload.get("message", "")
    attach_resume = payload.get("attach_resume", True)

    sent = []
    skipped = []
    failed = []

    for job in jobs:
        recruiter_email = (
            job.get("contact_email")
            or job.get("to_email")
            or job.get("email")
        )

        title = job.get("title") or job.get("job_title") or "Position"
        company = job.get("company") or "Company"

        if not recruiter_email:
            skipped.append({
                "title": title,
                "company": company,
                "reason": "No recruiter/contact email found",
            })
            continue

        subject = f"Application for {title}"

        try:
            result = send_email(
                to_email=recruiter_email,
                subject=subject,
                body=message,
                attach_resume=attach_resume,
            )

            sent.append({
                "title": title,
                "company": company,
                "email": recruiter_email,
                "gmail_message_id": result.get("id"),
                "status": "SENT",
                "resume_attached": attach_resume,
            })

        except Exception as e:
            failed.append({
                "title": title,
                "company": company,
                "email": recruiter_email,
                "error": str(e),
            })

    return {
        "success": len(failed) == 0,
        "sent_count": len(sent),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "sent": sent,
        "skipped": skipped,
        "failed": failed,
    }


@app.get("/api/applications")
def get_applications(limit: int = 200):
    outreach_path = first_existing(ROOT / "outreach_master.xlsx", EXPORTS / "outreach_master.xlsx")
    outreach_df = load_excel_any(outreach_path)

    if outreach_df.empty:
        return {"applications": []}

    date_col = find_col(outreach_df, ["sent_at", "applied_at", "date", "created_at"])

    if date_col:
        outreach_df["_sort_date"] = pd.to_datetime(outreach_df[date_col], errors="coerce")
        outreach_df = outreach_df.sort_values("_sort_date", ascending=False)

    if "_sort_date" in outreach_df.columns:
        outreach_df = outreach_df.drop(columns=["_sort_date"])

    return {"applications": df_to_records(outreach_df, limit)}


@app.get("/api/followups/due")
def get_due_followups(limit: int = 100):
    outreach_path = first_existing(ROOT / "outreach_master.xlsx", EXPORTS / "outreach_master.xlsx")
    outreach_df = load_excel_any(outreach_path)

    if outreach_df.empty:
        return {"followups": []}

    due_col = find_col(outreach_df, ["followup_due_at", "follow_up_due_at", "followup_due"])
    sent_col = find_col(outreach_df, ["followup_sent_at", "follow_up_sent_at"])

    if not due_col:
        return {"followups": []}

    outreach_df["_due_date"] = pd.to_datetime(outreach_df[due_col], errors="coerce")
    today = pd.Timestamp.now()

    due_df = outreach_df[
        outreach_df["_due_date"].notna()
        & (outreach_df["_due_date"] <= today)
    ]

    if sent_col:
        due_df = due_df[due_df[sent_col].fillna("").astype(str).str.strip() == ""]

    due_df = due_df.sort_values("_due_date", ascending=True)

    if "_due_date" in due_df.columns:
        due_df = due_df.drop(columns=["_due_date"])

    return {"followups": df_to_records(due_df, limit)}


@app.get("/api/debug/applications")
def debug_applications():
    outreach_path = first_existing(ROOT / "outreach_master.xlsx", EXPORTS / "outreach_master.xlsx")
    outreach_df = load_excel_any(outreach_path)

    if outreach_df.empty:
        return {"columns": []}

    return {
        "columns": outreach_df.columns.tolist(),
        "sample": outreach_df.head(3).fillna("").to_dict(orient="records"),
    }

@app.post("/api/followups/send")
def send_followups(payload: dict):
    followups = payload.get("followups", [])
    message = payload.get("message", "")

    sent = []
    skipped = []
    failed = []

    for item in followups:
        to_email = item.get("to_email") or item.get("email") or item.get("contact_email")
        subject = item.get("subject") or "Follow-up on my application"

        if not to_email:
            skipped.append({
                "subject": subject,
                "reason": "No recipient email found"
            })
            continue

        try:
            result = send_email_with_resume(
                to_email=to_email,
                subject=f"Follow-up: {subject}",
                body=message,
            )

            sent.append({
                "email": to_email,
                "subject": subject,
                "gmail_message_id": result.get("id"),
                "status": "SENT"
            })

        except Exception as e:
            failed.append({
                "email": to_email,
                "subject": subject,
                "error": str(e)
            })

    return {
        "success": len(failed) == 0,
        "sent_count": len(sent),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "sent": sent,
        "skipped": skipped,
        "failed": failed,
    }


@app.post("/api/jobs/mark-applied")
def mark_job_applied(payload: dict):
    job = payload.get("job", {})
    note = payload.get("note", "Marked manually applied from dashboard")

    if not job:
        return {
            "success": False,
            "message": "No job provided"
        }

    outreach_path = first_existing(
        ROOT / "outreach_master.xlsx",
        EXPORTS / "outreach_master.xlsx",
    )

    existing_df = load_excel_any(outreach_path)

    row = {
        "to_email": job.get("contact_email", ""),
        "to_name": job.get("company", ""),
        "subject": f"Manual Apply: {job.get('title', 'Position')}",
        "message_template": note,
        "status": "MANUAL_APPLIED",
        "followup_due_at": "",
        "followup_sent_at": "",
        "thread_id": "",
        "person_id": "",
        "send_flag": "manual",
        "sent_at": now(),
        "batch_id": "",
        "job_title": job.get("title", ""),
        "company": job.get("company", ""),
        "job_link": job.get("link", ""),
        "last_reply_at": "",
        "last_reply_snippet": "",
    }

    new_df = pd.DataFrame([row])

    final_df = pd.concat([existing_df, new_df], ignore_index=True) if not existing_df.empty else new_df

    output_path = EXPORTS / "outreach_master.xlsx"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_df.to_excel(output_path, index=False)

    return {
        "success": True,
        "message": "Job marked as manually applied",
        "job": row
    }
from app.supabase_db import supabase

@app.get("/api/test-db")
def test_db():
    data = supabase.table("jobs").select("*").limit(5).execute()
    return {"success": True, "data": data.data}
