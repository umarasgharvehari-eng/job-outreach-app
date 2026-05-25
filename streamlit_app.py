import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st

# ---------------------------
# Paths / Constants
# ---------------------------
ROOT = Path(__file__).resolve().parent
EXPORTS = ROOT / "exports"
STATE = ROOT / "services" / "state.json"
LOGF = ROOT / "services" / "worker.log"

st.set_page_config(page_title="Job Outreach Dashboard", layout="wide")
st.title("🚀 Job Outreach Automation Dashboard")


# ---------------------------
# Helpers (files + state)
# ---------------------------
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
    data["updated_at"] = datetime.now().isoformat(timespec="seconds")
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def start_worker():
    # set running flag true; worker will set pid on its own
    write_state(running=True)
    subprocess.Popen([sys.executable, "services/worker.py"], cwd=str(ROOT))


def stop_worker():
    write_state(running=False)


# ---------------------------
# Analytics Helpers
# ---------------------------
def _first_existing(*paths: Path) -> Path | None:
    for p in paths:
        if p and p.exists():
            return p
    return None


@st.cache_data(show_spinner=False)
def load_excel_any(path: Path) -> pd.DataFrame:
    """
    Loads all sheets and concatenates them (adds __sheet).
    """
    xls = pd.ExcelFile(path)
    dfs = []
    for sh in xls.sheet_names:
        df = pd.read_excel(path, sheet_name=sh)
        df["__sheet"] = sh
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols = {str(c).lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols:
            return cols[cand.lower()]
    for c in df.columns:
        cl = str(c).lower()
        for cand in candidates:
            if cand.lower() in cl:
                return c
    return None


def to_dt(series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def normalize_text(s) -> pd.Series:
    return s.fillna("").astype(str).str.lower().str.strip()


def is_positive_reply(text: pd.Series) -> pd.Series:
    t = normalize_text(text)
    positive_keywords = [
        "interested",
        "let's talk",
        "lets talk",
        "schedule",
        "meeting",
        "call",
        "interview",
        "next step",
        "proceed",
        "sounds good",
        "yes",
        "sure",
        "available",
        "book",
        "calendar",
        "invite",
    ]
    m = False
    for kw in positive_keywords:
        m = m | t.str.contains(kw, na=False)
    return m


def safe_value_counts(df: pd.DataFrame, col: str, top: int = 12) -> pd.DataFrame:
    vc = df[col].fillna("Unknown").astype(str).value_counts().head(top)
    out = vc.reset_index()
    out.columns = [col, "count"]
    return out


# ---------------------------
# Tabs
# ---------------------------
tabs = st.tabs(["Control Panel", "Analytics", "Logs"])

# =========================================================
# TAB 0: Control Panel
# =========================================================
with tabs[0]:
    st.subheader("Control Panel")

    st_state = read_state()
    running = st_state.get("running", False)

    c1, c2, c3 = st.columns(3)
    c1.metric("Worker Running", "YES" if running else "NO")
    c2.metric("Last Job", st_state.get("last_job", "-"))
    c3.metric("Last Job At", st_state.get("last_job_at", "-"))

    colA, colB, colC = st.columns(3)

    with colA:
        if st.button("▶ Start Worker", disabled=running):
            start_worker()
            st.success("Worker started")
            st.rerun()

    with colB:
        if st.button("⏹ Stop Worker", disabled=not running):
            stop_worker()
            st.warning("Worker stop requested")
            st.rerun()

    with colC:
        if st.button("⚡ Run Inbox Sync Now"):
            subprocess.run(
                [sys.executable, "-m", "scripts.45_run_inbox_fast"], cwd=str(ROOT)
            )
            st.success("Inbox sync done")
            st.rerun()

    st.divider()
    st.subheader("Worker Logs (latest 200)")
    if LOGF.exists():
        lines = LOGF.read_text(encoding="utf-8").splitlines()[-200:]
        st.code("\n".join(lines), language="text")
    else:
        st.info("No logs yet.")

# =========================================================
# TAB 1: Analytics
# =========================================================
with tabs[1]:
    st.subheader("📊 Analytics")

    outreach_path = _first_existing(
        ROOT / "outreach_master.xlsx",
        EXPORTS / "outreach_master.xlsx",
    )
    replies_path = _first_existing(
        ROOT / "replies_master.xlsx",
        EXPORTS / "replies_master.xlsx",
    )
    jobs_path = _first_existing(
        ROOT / "jobs_master.xlsx",
        EXPORTS / "jobs_master.xlsx",
    )

    outreach_df = load_excel_any(outreach_path) if outreach_path else pd.DataFrame()
    replies_df = load_excel_any(replies_path) if replies_path else pd.DataFrame()
    jobs_df = load_excel_any(jobs_path) if jobs_path else pd.DataFrame()

    st.markdown("### Data Sources")
    s1, s2, s3 = st.columns(3)
    s1.write(
        f"**Outreach:** `{outreach_path}`"
        if outreach_path
        else "**Outreach:** ❌ not found"
    )
    s2.write(
        f"**Replies:** `{replies_path}`"
        if replies_path
        else "**Replies:** ❌ not found"
    )
    s3.write(f"**Jobs:** `{jobs_path}`" if jobs_path else "**Jobs:** ❌ not found")

    if outreach_df.empty and replies_df.empty:
        st.warning(
            "Outreach/Replies master files not found or empty. Place them in root or exports folder."
        )
        st.stop()

    # Auto-detect columns
    outreach_date_col = pick_col(
        outreach_df,
        [
            "sent_at",
            "sent date",
            "date_sent",
            "created_at",
            "outreach_at",
            "timestamp",
            "date",
        ],
    )
    outreach_status_col = pick_col(
        outreach_df, ["status", "stage", "state", "outreach_status", "pipeline"]
    )
    outreach_source_col = pick_col(
        outreach_df, ["source", "platform", "channel", "job_source"]
    )
    outreach_emailid_col = pick_col(
        outreach_df, ["email_id", "message_id", "gmail_id", "thread_id", "id"]
    )

    replies_date_col = pick_col(
        replies_df,
        ["replied_at", "reply_at", "date", "received_at", "created_at", "timestamp"],
    )
    replies_text_col = pick_col(
        replies_df,
        ["body", "message", "reply", "text", "snippet", "content", "description"],
    )
    replies_emailid_col = pick_col(
        replies_df, ["email_id", "message_id", "gmail_id", "thread_id", "id"]
    )

    with st.expander(
        "⚙️ Column mapping (auto-detected — change if needed)", expanded=False
    ):
        colA, colB = st.columns(2)

        with colA:
            st.caption("Outreach")
            outreach_date_col = st.selectbox(
                "Outreach date column",
                options=["(none)"] + list(outreach_df.columns),
                index=(
                    (1 + list(outreach_df.columns).index(outreach_date_col))
                    if outreach_date_col in list(outreach_df.columns)
                    else 0
                ),
            )
            outreach_status_col = st.selectbox(
                "Outreach status column",
                options=["(none)"] + list(outreach_df.columns),
                index=(
                    (1 + list(outreach_df.columns).index(outreach_status_col))
                    if outreach_status_col in list(outreach_df.columns)
                    else 0
                ),
            )
            outreach_source_col = st.selectbox(
                "Outreach source column",
                options=["(none)"] + list(outreach_df.columns),
                index=(
                    (1 + list(outreach_df.columns).index(outreach_source_col))
                    if outreach_source_col in list(outreach_df.columns)
                    else 0
                ),
            )
            outreach_emailid_col = st.selectbox(
                "Outreach email-id column",
                options=["(none)"] + list(outreach_df.columns),
                index=(
                    (1 + list(outreach_df.columns).index(outreach_emailid_col))
                    if outreach_emailid_col in list(outreach_df.columns)
                    else 0
                ),
            )

        with colB:
            st.caption("Replies")
            replies_date_col = st.selectbox(
                "Replies date column",
                options=["(none)"] + list(replies_df.columns),
                index=(
                    (1 + list(replies_df.columns).index(replies_date_col))
                    if replies_date_col in list(replies_df.columns)
                    else 0
                ),
            )
            replies_text_col = st.selectbox(
                "Replies text/body column",
                options=["(none)"] + list(replies_df.columns),
                index=(
                    (1 + list(replies_df.columns).index(replies_text_col))
                    if replies_text_col in list(replies_df.columns)
                    else 0
                ),
            )
            replies_emailid_col = st.selectbox(
                "Replies email-id column",
                options=["(none)"] + list(replies_df.columns),
                index=(
                    (1 + list(replies_df.columns).index(replies_emailid_col))
                    if replies_emailid_col in list(replies_df.columns)
                    else 0
                ),
            )

        outreach_date_col = None if outreach_date_col == "(none)" else outreach_date_col
        outreach_status_col = (
            None if outreach_status_col == "(none)" else outreach_status_col
        )
        outreach_source_col = (
            None if outreach_source_col == "(none)" else outreach_source_col
        )
        outreach_emailid_col = (
            None if outreach_emailid_col == "(none)" else outreach_emailid_col
        )

        replies_date_col = None if replies_date_col == "(none)" else replies_date_col
        replies_text_col = None if replies_text_col == "(none)" else replies_text_col
        replies_emailid_col = (
            None if replies_emailid_col == "(none)" else replies_emailid_col
        )

    # Derived columns
    outreach_df["_dt"] = (
        to_dt(outreach_df[outreach_date_col]) if outreach_date_col else pd.NaT
    )
    replies_df["_dt"] = (
        to_dt(replies_df[replies_date_col]) if replies_date_col else pd.NaT
    )
    replies_df["_is_positive"] = (
        is_positive_reply(replies_df[replies_text_col]) if replies_text_col else False
    )

    # Join replies to outreach by email_id if possible
    joined_reply_count = None
    joined_positive_count = None

    if (
        outreach_emailid_col
        and replies_emailid_col
        and outreach_emailid_col in outreach_df.columns
        and replies_emailid_col in replies_df.columns
    ):
        o_ids = normalize_text(outreach_df[outreach_emailid_col])
        r_ids = normalize_text(replies_df[replies_emailid_col])

        reply_set = set(r_ids[r_ids != ""].tolist())
        pos_set = set(
            r_ids[(r_ids != "") & (replies_df["_is_positive"] == True)].tolist()
        )

        outreach_df["_has_reply"] = o_ids.isin(reply_set)
        outreach_df["_has_positive_reply"] = o_ids.isin(pos_set)

        joined_reply_count = int(outreach_df["_has_reply"].sum())
        joined_positive_count = int(outreach_df["_has_positive_reply"].sum())

    total_outreach = len(outreach_df) if not outreach_df.empty else 0
    total_replies = len(replies_df) if not replies_df.empty else 0

    reply_count_for_rate = (
        joined_reply_count if joined_reply_count is not None else total_replies
    )
    positive_count_for_rate = (
        joined_positive_count
        if joined_positive_count is not None
        else int(replies_df["_is_positive"].sum()) if not replies_df.empty else 0
    )

    reply_rate = (
        (reply_count_for_rate / total_outreach * 100) if total_outreach else 0.0
    )
    positive_rate = (
        (positive_count_for_rate / total_outreach * 100) if total_outreach else 0.0
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Outreach", f"{total_outreach:,}")
    k2.metric("Total Replies", f"{reply_count_for_rate:,}")
    k3.metric("Reply Rate", f"{reply_rate:.1f}%")
    k4.metric("Positive Rate", f"{positive_rate:.1f}%")

    st.divider()

    # Performance chart: sent vs replies (daily)
st.markdown("### 📈 Outreach Performance (Sent vs Replies)")

# Daily sent
if outreach_df["_dt"].notna().any():
    sent_daily = (
        outreach_df.dropna(subset=["_dt"])
        .assign(day=lambda d: d["_dt"].dt.date)
        .groupby("day")
        .size()
        .reset_index(name="sent")
    )
else:
    sent_daily = pd.DataFrame(columns=["day", "sent"])

# Daily replies
if replies_df["_dt"].notna().any():
    replies_daily = (
        replies_df.dropna(subset=["_dt"])
        .assign(day=lambda d: d["_dt"].dt.date)
        .groupby("day")
        .size()
        .reset_index(name="replies")
    )
else:
    replies_daily = pd.DataFrame(columns=["day", "replies"])

# Merge safely (day column always exists now)
perf = pd.merge(sent_daily, replies_daily, on="day", how="outer")

# ensure numeric columns properly typed
if "sent" in perf.columns:
    perf["sent"] = pd.to_numeric(perf["sent"], errors="coerce")
if "replies" in perf.columns:
    perf["replies"] = pd.to_numeric(perf["replies"], errors="coerce")

perf = perf.fillna({"sent": 0, "replies": 0})

if not perf.empty:
    perf["day"] = pd.to_datetime(perf["day"], errors="coerce")
    perf = perf.sort_values("day")
    st.line_chart(perf.set_index("day")[["sent", "replies"]])
else:
    st.info(
        "No daily data available yet (sent/replies dates are empty or not detected)."
    )

    if not sent_daily.empty or not replies_daily.empty:
        perf = pd.merge(sent_daily, replies_daily, on="day", how="outer")
        perf["sent"] = pd.to_numeric(perf.get("sent", 0), errors="coerce").fillna(0).astype(int)
        perf["replies"] = pd.to_numeric(perf.get("replies", 0), errors="coerce").fillna(0).astype(int)
        perf["day"] = pd.to_datetime(perf["day"])
        perf = perf.sort_values("day")
        st.line_chart(perf.set_index("day")[["sent", "replies"]])
    else:
        st.info(
            "No valid date columns detected for daily performance charts. Set date columns in the mapping panel above."
        )

    st.divider()

    # Weekly success tracker
    st.markdown("### ✅ Success Rate Tracker (Weekly)")

    if outreach_df["_dt"].notna().any():
        temp = outreach_df.dropna(subset=["_dt"]).copy()
        temp["week"] = temp["_dt"].dt.to_period("W").astype(str)
        weekly_sent = temp.groupby("week").size().reset_index(name="sent")

        if joined_reply_count is not None:
            weekly_reply = (
                temp.groupby("week")["_has_reply"].sum().reset_index(name="replies")
            )
            weekly_pos = (
                temp.groupby("week")["_has_positive_reply"]
                .sum()
                .reset_index(name="positive")
            )
        else:
            rtemp = replies_df.dropna(subset=["_dt"]).copy()
            rtemp["week"] = rtemp["_dt"].dt.to_period("W").astype(str)
            weekly_reply = rtemp.groupby("week").size().reset_index(name="replies")
            weekly_pos = (
                rtemp.groupby("week")["_is_positive"].sum().reset_index(name="positive")
            )

        weekly = (
            weekly_sent.merge(weekly_reply, on="week", how="left")
            .merge(weekly_pos, on="week", how="left")
            .fillna(0)
        )
        weekly["reply_rate_%"] = (weekly["replies"] / weekly["sent"] * 100).round(1)
        weekly["positive_rate_%"] = (weekly["positive"] / weekly["sent"] * 100).round(1)

        st.dataframe(
            weekly.sort_values("week", ascending=False), use_container_width=True
        )
        st.line_chart(weekly.set_index("week")[["reply_rate_%", "positive_rate_%"]])
    else:
        st.info(
            "Outreach date column not detected. Set it in the mapping panel to enable weekly success tracking."
        )

    st.divider()

    # Breakdowns
    st.markdown("### 🧩 Breakdowns")
    b1, b2 = st.columns(2)

    with b1:
        if outreach_source_col and outreach_source_col in outreach_df.columns:
            st.markdown("**By Source**")
            src = safe_value_counts(outreach_df, outreach_source_col, top=12)
            st.bar_chart(src.set_index(outreach_source_col)["count"])
        else:
            st.info("Source breakdown: map a source column in the panel above.")

    with b2:
        if outreach_status_col and outreach_status_col in outreach_df.columns:
            st.markdown("**By Status / Stage**")
            stt = safe_value_counts(outreach_df, outreach_status_col, top=12)
            st.bar_chart(stt.set_index(outreach_status_col)["count"])
        else:
            st.info("Status breakdown: map a status/stage column in the panel above.")

# =========================================================
# TAB 2: Logs
# =========================================================
with tabs[2]:
    st.subheader("Logs")

    st.caption("Worker log (latest 400 lines)")
    if LOGF.exists():
        lines = LOGF.read_text(encoding="utf-8").splitlines()[-400:]
        st.code("\n".join(lines), language="text")
    else:
        st.info("No logs yet.")
