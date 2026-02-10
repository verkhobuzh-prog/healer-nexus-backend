import sqlite3
try:
    conn = sqlite3.connect('healer_nexus.db')
    cursor = conn.execute('PRAGMA table_info(specialist_content)')
    print('\n🖼️ Колонки specialist_content:')
    for row in cursor:
        print(f'  - {row[1]} ({row[2]})')
    conn.close()
except Exception as e:
    print(f'❌ Помилка: {e}')
