import sqlite3
c = sqlite3.connect('healer_nexus.db')
print("=== USERS ===")
for r in c.execute("SELECT id, email, role, username FROM users").fetchall():
    print(f"  id={r[0]}, email={r[1]}, role={r[2]}, name={r[3]}")
print("\n=== PRACTITIONERS ===")
for r in c.execute("SELECT id, user_id, specialist_id FROM practitioner_profiles").fetchall():
    print(f"  id={r[0]}, user_id={r[1]}, specialist_id={r[2]}")
print("\n=== SPECIALISTS ===")
for r in c.execute("SELECT id, name, specialty FROM specialists").fetchall():
    print(f"  id={r[0]}, name={r[1]}, specialty={r[2]}")
print("\n=== BLOG POSTS ===")
for r in c.execute("SELECT id, practitioner_id, title, status FROM blog_posts").fetchall():
    print(f"  id={r[0]}, practitioner={r[1]}, title={r[2]}, status={r[3]}")
c.close()