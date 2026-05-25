# app/parsers.py
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse

ALLOWED_DOMAINS = {
    "linkedin.com",
    "www.linkedin.com",
    "indeed.com",
    "pk.indeed.com",
    "freelancer.com",
    "www.freelancer.com",
    "rozee.pk",
    "www.rozee.pk",
    "jobs.com",
    "www.jobs.com",
}

EMAIL_RE = re.compile(r"([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})")

BAD_EMAIL_PARTS = [
    "noreply", "no-reply", "donotreply", "do-not-reply",
    "support", "help", "mailer-daemon", "postmaster"
]

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

    # Prefer emails on keyword lines
    for ln in lines:
        ln_low = ln.lower()
        if any(k in ln_low for k in keywords):
            emails = EMAIL_RE.findall(ln)
            for e in emails:
                if good(e):
                    return e.strip().lower()

    # Fallback: any email in full text
    for e in EMAIL_RE.findall(text):
        if good(e):
            return e.strip().lower()

    return None

def _html_to_text(body: str) -> str:
    text = body or ""
    if "<html" in text.lower():
        soup = BeautifulSoup(text, "lxml")
        text = soup.get_text("\n")
    return text.strip()

def _all_urls(text: str) -> list[str]:
    urls = re.findall(r"https?://\S+", text or "")
    cleaned = []
    for u in urls:
        u = u.strip().rstrip(").,]}>\"'")
        cleaned.append(u)
    return cleaned

def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""

def _detect_source_from_url(url: str) -> str | None:
    d = _domain(url)
    if "indeed" in d:
        return "Indeed"
    if "linkedin" in d:
        return "LinkedIn"
    if "freelancer" in d:
        return "Freelancer"
    if "rozee" in d:
        return "Rozee"
    if "jobs.com" in d:
        return "Jobs.com"
    return None

def _pick_best_job_url(urls: list[str]) -> tuple[str | None, str | None]:
    """
    Returns (best_url, source)
    Only returns allowlisted sources.
    LinkedIn: must be a /jobs link.
    """
    for u in urls:
        src = _detect_source_from_url(u)
        if not src:
            continue

        d = _domain(u)
        if d not in ALLOWED_DOMAINS:
            continue

        if src == "LinkedIn":
            lu = u.lower()
            if "linkedin.com/jobs" in lu or "/jobs/" in lu:
                return u, "LinkedIn"
            continue

        return u, src

    return None, None

def _extract_contact_email(text: str, from_email: str = "") -> str | None:
    if not text:
        return None

    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    keywords = ["send", "email", "resume", "cv", "contact", "apply", "reach", "hr", "mail"]

    # 1) Prefer emails found on lines that include keywords
    for ln in lines:
        ln_low = ln.lower()
        if any(k in ln_low for k in keywords):
            emails = EMAIL_RE.findall(ln)
            for e in emails:
                el = e.strip().lower()
                if "example.com" in el:
                    continue
                if any(b in el for b in BAD_EMAIL_PARTS):
                    continue
                if "linkedin" in el or "indeed" in el or "glassdoor" in el:
                    continue
                if "umarasgharvehari" in el:
                    continue
                if from_email and el in from_email.lower():
                    continue
                return el

    # 2) fallback: any email in whole text
    for e in EMAIL_RE.findall(text):
        el = e.strip().lower()
        if "example.com" in el:
            continue
        if any(b in el for b in BAD_EMAIL_PARTS):
            continue
        if "linkedin" in el or "indeed" in el or "glassdoor" in el:
            continue
        if "umarasgharvehari" in el:
            continue
        if from_email and el in from_email.lower():
            continue
        return el

    return None

def parse_job(subject: str, body: str, from_email: str = "") -> dict:
    text = _html_to_text(body)
    urls = _all_urls(text)

    best_url, source = _pick_best_job_url(urls)

    # ✅ If not from allowed sources => reject
    if not best_url or not source:
        return {
            "is_job": False,
            "source": "Other",
            "title": None,
            "company": None,
            "location": None,
            "link": None,
            "contact_email": None,
            "description": text[:1200],
        }

    title = subject.strip() if subject else "Job"

    contact_email = _extract_contact_email(text, from_email=from_email)

    return {
        "is_job": True,
        "source": source,
        "title": title,
        "company": None,
        "location": None,
        "link": best_url,
        "contact_email": contact_email,   # ✅ NEW
        "description": text[:2500],
    }