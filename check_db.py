import sqlite3
db_file = 'healer_nexus.db'
try:
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cur.fetchall()]
    print(f"\n--- РЕАЛЬНІСТЬ БАЗИ: {db_file} ---")
    print(f"Таблиці: {', '.join(tables) if tables else 'ПОРОЖНЬО'}")
    if 'specialists' in tables:
        cur.execute("SELECT COUNT(*) FROM specialists")
        print(f"Спеціалістів: {cur.fetchone()[0]}")
    if 'posts' in tables:
        cur.execute("SELECT COUNT(*) FROM posts WHERE status='draft'")
        print(f"Чернеток: {cur.fetchone()[0]}")
    else:
        print("⚠️ Таблиця 'posts' ВІДСУТНЯ!")
    conn.close()
except Exception as e:
    print(f"Помилка: {e}")
