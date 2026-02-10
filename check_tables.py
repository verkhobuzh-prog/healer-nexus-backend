import sqlite3
conn = sqlite3.connect('healer_nexus.db')
tables = conn.execute('SELECT name FROM sqlite_master WHERE type="table"').fetchall()
print('Таблиці:', [t[0] for t in tables])
conn.close()
