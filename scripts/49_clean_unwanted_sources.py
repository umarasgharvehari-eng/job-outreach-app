# scripts/49_clean_unwanted_sources.py

import sqlite3

conn = sqlite3.connect("data/bot.db")
cur = conn.cursor()

print("Before cleanup:")
print(cur.execute("SELECT source, COUNT(*) FROM jobs GROUP BY source").fetchall())

# 1️⃣ Remove Other
cur.execute("DELETE FROM jobs WHERE source = 'Other'")

# 2️⃣ Remove old EmailAlert entries
cur.execute("DELETE FROM jobs WHERE source = 'EmailAlert'")

# 3️⃣ Remove LinkedIn non-job links
cur.execute("""
DELETE FROM jobs
WHERE source = 'LinkedIn'
AND (
    link IS NULL
    OR link NOT LIKE '%linkedin.com/jobs%'
    AND link NOT LIKE '%/jobs/%'
)
""")

conn.commit()

print("\nAfter cleanup:")
print(cur.execute("SELECT source, COUNT(*) FROM jobs GROUP BY source").fetchall())

conn.close()
print("\nCleanup completed ✅")
