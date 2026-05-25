from app.gmail_client import get_gmail_service
from app.followup_service import run_followups
from app.replies_service import capture_replies_from_threads


def main():
    # Get Gmail service
    svc = get_gmail_service()

    # Run followups
    followups_sent = run_followups(svc)

    # Capture replies
    replies_captured = capture_replies_from_threads(svc)

    print("Followups sent:", followups_sent)
    print("Replies captured:", replies_captured)


if __name__ == "__main__":
    main()
