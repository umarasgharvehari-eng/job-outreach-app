import re

CONTACT_HINTS = [
    "send your cv", "send resume", "email your cv", "email resume",
    "send your resume", "apply by emailing", "contact", "reach out",
    "resume to", "cv to", "send to", "email to", "mail to"
]

IGNORE_EMAIL_KEYWORDS = [
    "noreply", "no-reply", "do-not-reply", "donotreply",
    "linkedin", "indeed", "glassdoor", "freelancer", "rozee"
]

def _extract_contact_email(text: str, from_email: str = "") -> str | None:
    t = (text or "")
    emails = re.findall(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", t)
    if not emails:
        return None

    # normalize + unique keep order
    seen = set()
    cleaned = []
    for e in emails:
        e2 = e.strip().lower()
        if e2 in seen:
            continue
        seen.add(e2)
        cleaned.append(e2)

    # filter obvious junk (platform/noreply)
    def ok(e: str) -> bool:
        if any(k in e for k in IGNORE_EMAIL_KEYWORDS):
            return False
        # don't pick your own email if present
        if "umarasgharvehari" in e:
            return False
        return True

    cleaned = [e for e in cleaned if ok(e)]
    if not cleaned:
        return None

    # prefer emails near hint lines
    lines = [ln.strip().lower() for ln in t.splitlines() if ln.strip()]
    for e in cleaned:
        for ln in lines[:400]:
            if e in ln and any(h in ln for h in CONTACT_HINTS):
                return e

    # fallback: first valid email
    return cleaned[0]