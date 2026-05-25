import os
import time
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

import schedule

ROOT = Path(__file__).resolve().parent.parent
SERVICE_DIR = Path(__file__).resolve().parent

STATE = SERVICE_DIR / "state.json"
LOGF = SERVICE_DIR / "worker.log"


def now():
    return datetime.now().isoformat(timespec="seconds")


def log(msg: str):
    line = f"[{now()}] {msg}"
    print(line)

    LOGF.parent.mkdir(parents=True, exist_ok=True)

    with open(LOGF, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_state() -> dict:
    if not STATE.exists():
        return {}

    try:
        txt = STATE.read_text(encoding="utf-8").strip()
        return json.loads(txt) if txt else {}
    except Exception as e:
        log(f"WARN: failed to read state.json ({e})")
        return {}


def set_state(**kwargs):
    data = read_state()
    data.update(kwargs)
    data["updated_at"] = now()

    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def acquire_lock(lock_name: str) -> bool:
    state = read_state()

    if state.get("job_lock"):
        return False

    set_state(
        job_lock=lock_name,
        job_lock_at=now(),
    )

    return True


def release_lock(lock_name: str):
    state = read_state()

    if state.get("job_lock") == lock_name:
        set_state(
            job_lock=None,
            job_lock_at=None,
        )


def run_module(module_name: str, lock_name: str):
    if not acquire_lock(lock_name):
        log(f"SKIP: {module_name} lock busy: {read_state().get('job_lock')}")
        return False

    started_at = now()

    set_state(
        last_job=lock_name,
        last_job_at=started_at,
        last_job_status="running",
    )

    try:
        log(f"RUN: {module_name}")

        result = subprocess.run(
            [sys.executable, "-m", module_name],
            cwd=str(ROOT),
        )

        success = result.returncode == 0

        set_state(
            last_job=lock_name,
            last_job_finished_at=now(),
            last_job_status="success" if success else "failed",
            last_job_return_code=result.returncode,
        )

        if success:
            log(f"DONE: {module_name}")
        else:
            log(f"ERROR: {module_name} failed with code {result.returncode}")

        return success

    except Exception as e:
        set_state(
            last_job=lock_name,
            last_job_finished_at=now(),
            last_job_status="error",
            last_job_error=str(e),
        )

        log(f"ERROR: {module_name} exception: {e}")
        return False

    finally:
        release_lock(lock_name)


def job_inbox_fast():
    run_module(
        "scripts.45_run_inbox_fast",
        lock_name="inbox_fast",
    )


def outreach_batch():
    run_module(
        "scripts.40_run_batch",
        lock_name="outreach_batch",
    )


def followups():
    run_module(
        "scripts.41_run_followups",
        lock_name="followups",
    )


def update_schedule_state():
    jobs = []

    for job in schedule.jobs:
        jobs.append(
            {
                "job": str(job.job_func),
                "next_run": job.next_run.isoformat(timespec="seconds") if job.next_run else None,
            }
        )

    set_state(schedule=jobs)


def main():
    pid = os.getpid()

    state = read_state()
    existing_pid = state.get("worker_pid")

    if state.get("running") is True and existing_pid and existing_pid != pid:
        log(f"Another worker appears running pid={existing_pid}. Exiting.")
        return

    log(f"Worker started pid={pid}")

    set_state(
        running=True,
        worker_pid=pid,
        started_at=now(),
        stopped_at=None,
        last_job_status=None,
    )

    schedule.clear()

    schedule.every(5).minutes.do(job_inbox_fast)
    schedule.every(15).minutes.do(outreach_batch)
    schedule.every().day.at("11:05").do(followups)

    update_schedule_state()

    log("Initial inbox sync starting")
    job_inbox_fast()

    while True:
        state = read_state()

        if state.get("running") is False:
            log("Worker stopping because running=false")
            break

        schedule.run_pending()
        update_schedule_state()
        time.sleep(2)

    set_state(
        running=False,
        stopped_at=now(),
        worker_pid=None,
        job_lock=None,
        job_lock_at=None,
    )

    log("Worker stopped")


if __name__ == "__main__":
    main()