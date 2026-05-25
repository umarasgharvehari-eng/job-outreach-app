import subprocess
import sys

def run(cmd):
    print("\nRUN:", cmd)
    r = subprocess.run([sys.executable, "-m", cmd], capture_output=False)
    if r.returncode != 0:
        raise SystemExit(r.returncode)

def main():
    run("scripts.06_jobs_to_master")
    # ✅ add replies sync here
    run("scripts.03_followups_and_replies")
    run("scripts.03_followups_and_replies")  # or 05_followups_and_replies_master (see note)
    run("scripts.44_export_jobs_daily_from_master")
    run("scripts.21_sync_to_google_sheet")

if __name__ == "__main__":
    main()