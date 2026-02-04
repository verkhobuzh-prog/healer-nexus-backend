# Аналіз стану проекту Healer Nexus

**Дата:** 31.01.2025  
**Корінь репо:** `healer-backend`  
**Робоча частина:** `backend/` (FastAPI, app, alembic, docker)

---

## 1. Структура проекту

```
healer-backend/
├── .gitignore              # кореневий (venv, .env, __pycache__, *.sqlite3, IDE)
├── backend/
│   ├── .gitignore          # детальніший (Python, DB, logs, backups, IDE)
│   ├── alembic/            # міграції (project_id, role для specialists)
│   ├── app/
│   │   ├── ai/             # Gemini, self_reflection, moderation, analytics
│   │   ├── api/            # chat, specialists, services, health, auth
│   │   ├── automation/     # monitoring, scheduler
│   │   ├── config.py       # Settings з .env, structured logging
│   │   ├── core/           # event_bus, module_registry, base_module
│   │   ├── database/       # connection (async engine, init_db, get_db)
│   │   ├── models/         # User, Specialist, Message, Healer, Base
│   │   ├── modules/        # specialists_module
│   │   ├── resilience/     # safe_mode, self_heal
│   │   ├── schemas/        # responses, specialist, validation
│   │   ├── services/       # memory, simple_analytics
│   │   ├── static/         # HTML/CSS/JS (index, dashboard, admin, tracker)
│   │   ├── telegram/       # healer_bot, bot_runner, admin_bot, simple_bot
│   │   └── main.py         # FastAPI app, lifespan, роутери
│   ├── app_backup_before_fix/   # резервна копія коду (не для продакшену)
│   ├── legacy/             # старі API, БД, міграції
│   ├── scripts/            # reseed, seed_hybrid, seed_refactored
│   ├── docker-compose.yml  # db (Postgres), redis, admin-agent, web-api
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   └── README.md
```

**Висновок:** Структура зрозуміла: один backend-проект з app, міграціями, docker і документацією. Є дублювання (кореневий і backend `.gitignore`), бекопи та legacy — варто не плутати робочий код з ними.

---

## 2. Конфігурація та середовище

- **Конфіг:** `app/config.py` — Pydantic Settings, читання з `backend/.env` (BASE_DIR = parent of `app`).
- **Ключові змінні:** `PROJECT_ID`, `GEMINI_API_KEY`, `DATABASE_URL`, `TELEGRAM_BOT_TOKEN`, `ADMIN_CHAT_ID`, `API_BASE_URL`, `REDIS_URL`, `SECRET_KEY`, `CRITICAL_CPU/RAM`.
- **БД за замовчуванням:** `postgresql+asyncpg://...` — для локальної розробки часто перевизначають на `sqlite+aiosqlite:///./healer.db` або подібне.
- **Логи:** `backend/logs/`, RotatingFileHandler, structured logging з project_id/component.

**Ризики:** Якщо `.env` не створено, `GEMINI_API_KEY` і `TELEGRAM_BOT_TOKEN` порожні — AI і бот не працюватимуть (є попередження в логах). `SECRET_KEY` за замовчуванням — "change-me-in-production".

---

## 3. База даних та міграції

- **Рух:** SQLAlchemy 2.0 async; підтримка SQLite (aiosqlite) і PostgreSQL (asyncpg). Alembic — синхронний URL (sqlite/psycopg2) у `env.py`.
- **Моделі:** `User`, `Specialist`, `Message`, `Healer`; Base + TimestampMixin. У Specialist є `project_id`, `role`, `specialty` (і property `specialization`), `service_type`, `delivery_method`, `is_ai_powered` тощо.
- **Життєвий цикл:** При старті додатку викликається `init_db()` — створюються таблиці з `Base.metadata.create_all`. Міграції Alembic окремо (project_id, role тощо).
- **Файл БД:** У проєкті присутній `your_db.sqlite` — він має бути в `.gitignore` (у backend є `*.sqlite3`, `*.db`; кореневий — `*.sqlite3`, `*.db`). Ім’я `*.sqlite` варто додати в ігнор, якщо не ігнорується.

**Висновок:** Моделі та підключення готові до мультипроекту та двох драйверів БД. Потрібно слідкувати, щоб локальні `.sqlite`/`.db` не потрапляли в репо.

---

## 4. API (FastAPI)

| Група       | Ендпоінт | Опис |
|------------|----------|------|
| **Chat**   | `POST /api/chat` | Повідомлення до AI; при падінні AI — fallback пошук спеціалістів за ключовими словами (safe mode). |
| **Specialists** | `POST /api/specialists` | Створення (project_id, role, specialty/specialization). |
| | `GET /api/specialists` | Список активних (фільтр service_type, limit). |
| | `GET /api/specialists/{id}` | Один спеціаліст (404 якщо не знайдено). |
| | `PATCH /api/specialists/{id}` | Оновлення (404 якщо не знайдено). |
| | `DELETE /api/specialists/{id}` | Soft delete (is_active=False), 404 якщо не знайдено. |
| **Services** | `GET /api/services` | Каталог послуг. |
| | `GET /api/services/trending` | Трендові послуги (simple_analytics). |
| **Health** | `GET /api/health` | Базовий стан. |
| | `GET /api/health/detailed` | Детальні перевірки. |
| | `GET /api/health/full` | Повна діагностика (HealthChecker, ModuleRegistry). |
| | `GET /api/startup-check` | Перевірка успішного старту (модулі, EventBus, БД). |
| **Auth**   | `POST /api/register` | Реєстрація (auth.py) — **роутер не підключено в main.py**, тому ендпоінт недоступний. |

**Сторінки (без схеми):** `/`, `/dashboard`, `/admin`, `/tracker` — віддача статичних HTML.  
**Документація:** `/docs`, `/redoc`.

**Висновок:** Chat, specialists, services, health покриті та узгоджені з моделями/схемами. Auth реалізований у коді, але не підключений до додатку — щоб мати `/api/register`, потрібно додати `auth_router` у `main.py`.

---

## 5. AI та чат

- **Провайдер:** `app/ai/providers.py` — Gemini (google-genai), модель `gemini-1.5-flash`. Ключ із `settings.GEMINI_API_KEY`.
- **Чат:** Первинно — відповідь від AI; при помилці — пошук спеціалістів за словами з повідомлення (name/role/specialty), відповідь у safe mode з списком рекомендацій або підказкою про `/api/specialists`.
- **Допоміжне:** self_reflection (detect_service, intent, anxiety_score), moderation, analytics — використовуються в логіці провайдера/чатів.

**Висновок:** Логіка чату та fallback узгоджені; стабільність залежить від наявності та валідності GEMINI_API_KEY.

---

## 6. Telegram

- **Запуск:** У `lifespan` викликається `start_bot_process()` (bot_runner) — у фоновому потоці запускається Healer Nexus bot (healer_bot).
- **Боти:** `healer_bot.py` (основний клієнтський), `admin_bot.py`, `simple_bot.py`, `bot.py`, `notifications.py` — залежать від `TELEGRAM_BOT_TOKEN` та при потребі `ADMIN_CHAT_ID`.
- **Інтеграція:** Чат з користувачем, виклик AI (get_ai_provider), кнопки, збереження історії (memory) з прив’язкою до project_id.

**Висновок:** Інфраструктура бота є; коректність роботи залежить від налаштування токену та (для адмін-функцій) ADMIN_CHAT_ID.

---

## 7. Інфраструктура та фон

- **EventBus:** Заглушка в `app/core/event_bus.py` (connect/disconnect/emit/subscribe) — використовується ModuleRegistry, реальний Redis/Pub-Sub не підключено.
- **ModuleRegistry:** Реєстрація модулів, init_event_bus, get_overall_status, дочірні проекти — для моніторингу та майбутнього оркестрування.
- **Метрики:** Фонова задача `_metrics_collector()` раз на 60 с — CPU/RAM/диск (psutil), при перевищенні порогів — опційні Telegram-сповіщення (з cooldown).
- **Docker:** docker-compose — Postgres, Redis, admin-agent, web-api; секрети очікуються з `.env` (env_file), не захардкоджені в yml.

**Висновок:** Платформа запускається, БД ініціалізується, бот і метрики стартують. EventBus і Redis поки що не обов’язкові для базового сценарію.

---

## 8. Залежності та репозиторій

- **requirements.txt:** Перелічені core (FastAPI, uvicorn, pydantic, sqlalchemy, google-genai, python-dotenv, alembic), БД (aiosqlite, asyncpg, psycopg2-binary), auth (passlib[bcrypt]), моніторинг (psutil), Telegram (python-telegram-bot, httpx). Відповідає використанню в коді.
- **.gitignore:** Кореневий і backend — venv, .env, __pycache__, *.db, *.sqlite3, логи, IDE. У backend додатково — logs, backups, .vscode/.idea. Рекомендація: переконатися, що `*.sqlite` теж ігнорується, якщо такий файл з’являється.

**Висновок:** Залежності описані коректно; репозиторій захищений від випадкового коміту середовища та локальних БД за умови дотримання .gitignore.

---

## 9. Підсумкова таблиця

| Аспект            | Стан | Примітка |
|--------------------|-----|----------|
| Структура          | ✅  | Зрозуміла, є бекопи та legacy — не плутати з робочим кодом. |
| Конфіг і .env      | ✅  | Централізовано; потрібен .env з ключами для AI/Telegram. |
| БД і міграції      | ✅  | SQLite/Postgres, project_id, role; init_db + Alembic. |
| API (chat, specialists, services, health) | ✅ | Працюють, 404/500 оброблені, fallback чату є. |
| API (auth)         | ⚠️  | Реалізовано в auth.py, роутер не підключено в main. |
| AI (Gemini)        | ✅  | gemini-1.5-flash, ключ з settings. |
| Telegram bot       | ✅  | Запускається з main, залежить від токену. |
| EventBus / Redis   | ⚠️  | Заглушка/не використовується в основному флоу. |
| Метрики та моніторинг | ✅ | Фонова задача, опційні алерти в Telegram. |
| requirements.txt   | ✅  | Актуальний. |
| .gitignore         | ✅  | Секрети та БД не комітяться при дотриманні правил. |

---

## 10. Рекомендації

1. **Підключити auth:** У `main.py` додати `from app.api.auth import router as auth_router` і `app.include_router(auth_router, prefix="/api", tags=["Auth"])`, якщо потрібен публічний ендпоінт реєстрації.
2. **Переконатися в .gitignore:** Щоб у репо не потрапляли `*.sqlite`, `your_db.sqlite`, `logs/` — перевірити обидва .gitignore (корінь і backend).
3. **Документація:** Оновити README: який за замовчуванням DATABASE_URL (SQLite vs Postgres), що обов’язково в .env (GEMINI_API_KEY, TELEGRAM_BOT_TOKEN), і що auth за замовчуванням вимкнено (роутер не підключено).
4. **Продакшен:** Змінити SECRET_KEY, переглянути CORS, при потребі обмежити алерти метрик або вимкнути їх у dev.

Цей документ можна використовувати як знімок стану проекту та чеклист перед релізом або міграцією на GitHub.
