import subprocess, sys

def run(cmd):
    r = subprocess.run([sys.executable, "-m", cmd], capture_output=False)
    if r.returncode != 0:
        raise SystemExit(r.returncode)

def main():
    run("scripts.06_jobs_to_master")
    run("scripts.21_sync_to_google_sheet")

if __name__ == "__main__":
    main()
