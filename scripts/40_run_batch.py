import subprocess
import sys

def run(cmd):
    print("\nRUN:", cmd)
    r = subprocess.run([sys.executable, "-m", cmd], capture_output=False)
    if r.returncode != 0:
        raise SystemExit(r.returncode)

def main():
    run("scripts.31_generate_outreach_rows_from_sheet")
    run("scripts.33_sheet_outreach_to_excel_master")
    run("scripts.04_send_from_master_excel")
    run("scripts.34_sync_outreach_db_to_sheet")
    run("scripts.21_sync_to_google_sheet")

if __name__ == "__main__":
    main()
