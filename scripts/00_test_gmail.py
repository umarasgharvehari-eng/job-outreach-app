import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.gmail_client import get_gmail_service


def main():
    svc = get_gmail_service()
    profile = svc.users().getProfile(userId="me").execute()
    print("Authenticated:", profile["emailAddress"])

if __name__ == "__main__":
    main()
