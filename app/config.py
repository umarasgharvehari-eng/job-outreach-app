from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DB_PATH = ROOT / "data" / "bot.db"
EXPORT_DIR = ROOT / "exports"
ATTACHMENTS_DIR = ROOT / "attachments"

CREDENTIALS_PATH = ROOT / "credentials.json"
TOKEN_PATH = ROOT / "token.json"

CV_PDF_PATH = ATTACHMENTS_DIR / "Umar_CV.pdf"

FOLLOWUP_DAYS = 7


FOLLOWUP_TEMPLATE = """Hi {name},

Just following up on my previous email. Please let me know if you need anything else from my side.

Thanks,
Umar
"""

