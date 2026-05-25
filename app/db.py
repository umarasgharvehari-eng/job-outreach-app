import sqlite3
from app.config import DB_PATH

def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    schema = """
    CREATE TABLE IF NOT EXISTS jobs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source TEXT NOT NULL,
      received_at TEXT NOT NULL,
      subject TEXT,
      title TEXT,
      company TEXT,
      location TEXT,
      link TEXT,
      description TEXT,
      from_email TEXT,
      gmail_message_id TEXT UNIQUE,
      created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS outreach (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      job_id INTEGER,
      to_email TEXT NOT NULL,
      to_name TEXT,
      subject TEXT NOT NULL,
      sent_at TEXT NOT NULL,
      followup_due_at TEXT NOT NULL,
      followup_sent_at TEXT,
      status TEXT NOT NULL,
      gmail_thread_id TEXT,
      gmail_sent_message_id TEXT,
      last_checked_at TEXT,
      created_at TEXT NOT NULL,
      FOREIGN KEY(job_id) REFERENCES jobs(id)
    );

    CREATE TABLE IF NOT EXISTS replies (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      outreach_id INTEGER NOT NULL,
      reply_at TEXT NOT NULL,
      from_email TEXT NOT NULL,
      subject TEXT,
      body_snippet TEXT,
      gmail_message_id TEXT UNIQUE,
      gmail_thread_id TEXT,
      created_at TEXT NOT NULL,
      FOREIGN KEY(outreach_id) REFERENCES outreach(id)
    );

    CREATE INDEX IF NOT EXISTS idx_outreach_status ON outreach(status);
    CREATE INDEX IF NOT EXISTS idx_outreach_followup_due ON outreach(followup_due_at);
    CREATE INDEX IF NOT EXISTS idx_replies_outreach_id ON replies(outreach_id);
    """
    with get_conn() as conn:
        conn.executescript(schema)
        conn.commit()
