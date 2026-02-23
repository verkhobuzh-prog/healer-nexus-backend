import sqlite3
c = sqlite3.connect('healer_nexus.db')
tables = [t[0] for t in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("=== TABLES ===")
for t in sorted(tables):
    count = c.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
    print(f"  {t}: {count} rows")
c.close()
