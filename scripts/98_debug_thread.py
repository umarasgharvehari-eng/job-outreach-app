from app.gmail_client import get_gmail_service

THREAD_ID = "19c6665b33f0e4b2"  # <- aap apna thread id yahan paste kar do

def main():
    svc = get_gmail_service()
    t = svc.users().threads().get(userId="me", id=THREAD_ID, format="full").execute()
    msgs = t.get("messages", [])

    print("Thread:", THREAD_ID)
    print("Messages:", len(msgs))

    for i, m in enumerate(msgs, 1):
        headers = {h["name"].lower(): h["value"] for h in m.get("payload", {}).get("headers", [])}
        frm = headers.get("from", "")
        subj = headers.get("subject", "")
        dt = headers.get("date", "")
        print(f"{i}. from={frm} | subject={subj} | date={dt} | id={m.get('id')} | snippet={m.get('snippet','')[:80]}")

if __name__ == "__main__":
    main()
