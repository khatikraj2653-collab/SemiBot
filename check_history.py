import sqlite3
conn = sqlite3.connect("semibot_checkpoints.db")
schema = conn.execute("SELECT sql FROM sqlite_master WHERE name='analysis_history'").fetchone()
print("SCHEMA:", schema)
count = conn.execute("SELECT COUNT(*) FROM analysis_history").fetchone()
print("TOTAL ROWS:", count)
rows = conn.execute("SELECT * FROM analysis_history LIMIT 2").fetchall()
for r in rows:
    print(r)
conn.close()
