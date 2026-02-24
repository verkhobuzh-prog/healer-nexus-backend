import sqlite3
from datetime import datetime
conn = sqlite3.connect('healer_nexus.db')
c = conn.cursor()
try:
    # 1. Створюємо юзера
    c.execute("INSERT INTO users (username, email, role, is_active) VALUES (?, ?, ?, ?)", 
              ("anton_zabolotnyi", "zabolotnii333@i.ua", "practitioner", 1))
    user_id = c.lastrowid
    # 2. Додаємо спеціаліста (додано is_ai_powered та ai_model)
    c.execute("""
        INSERT INTO specialists (
            user_id, name, service_type, service_types, delivery_method, 
            specialty, hourly_rate, bio, telegram_id, is_verified, is_active, 
            is_ai_powered, ai_model,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, 
        "Антон Заболотний", 
        "healing", 
        '["regressology", "karmology", "healing"]', 
        "online",
        "Цілитель, регресолог, кармолог", 
        0, 
        "Діагностика і зцілення душі і тіла. Тел: +8613430583351", 
        "anton_miraton", 
        1, 1, 
        0, None,  # is_ai_powered = 0 (False), ai_model = None
        datetime.now().isoformat(), 
        datetime.now().isoformat()
    ))
    spec_id = c.lastrowid
    # 3. Додаємо SEO профіль
    slug = f"anton-zabolotnyi-{spec_id}"
    c.execute("""
        INSERT INTO practitioner_profiles (specialist_id, slug, project_id) 
        VALUES (?, ?, ?)
""", (spec_id, slug, "healer-nexus"))
    conn.commit()
    print(f"🚀 Антон успішно доданий! ID: {spec_id}, Slug: {slug}")
except sqlite3.Error as e:
    print(f"❌ Помилка бази даних: {e}")
finally:
    conn.close()
