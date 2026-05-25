import sqlite3

DB_PATH = "data/bot.db"

def add_col(cur, table, col_def):
    # col_def like: "last_reply_at TEXT"
    col_name = col_def.split()[0]
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    if col_name in cols:
        return False
    cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
    return True

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    changed = False
    changed |= add_col(cur, "outreach", "last_reply_at TEXT")
    changed |= add_col(cur, "outreach", "last_reply_snippet TEXT")

    if changed:
        conn.commit()
        print("Migration applied ✅ (reply columns added)")
    else:
        print("No changes needed ✅ (columns already exist)")

    conn.close()

if __name__ == "__main__":
    main()
