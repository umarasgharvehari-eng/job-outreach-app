import subprocess, sys

def run(cmd):
    print("\nRUN:", cmd)
    r = subprocess.run([sys.executable, "-m", cmd], capture_output=False)
    if r.returncode != 0:
        raise SystemExit(r.returncode)

def main():
    run("scripts.05_followups_and_replies_master")
    run("scripts.34_sync_outreach_db_to_sheet")
    run("scripts.21_sync_to_google_sheet")

if __name__ == "__main__":
    main()
