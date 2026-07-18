import sqlite3
for db in ["semibot_checkpoints.db", "factor_cache.db", "tools/semibot_checkpoints.db"]:
    try:
        conn = sqlite3.connect(db)
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        print(db, "->", tables)
        conn.close()
    except Exception as e:
        print(db, "ERROR:", e)
