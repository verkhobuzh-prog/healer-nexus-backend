# Аудит архітектури, БД та «білих плям»

**Дата:** 2026-03-10  
**Обсяг:** Backend (FastAPI + asyncpg), інфраструктура, фронтенд (React/HTML), БД, Telegram webhook, Auth (JWT), обробка помилок.

---

## 1. Екстракція архітектурного шуму (стеки)

### 1.1 Backend: FastAPI + asyncpg, legacy vs app/

**Висновок:** Робочий код повністю в `app/`. Legacy не підключається.

| Зона | Стан |
|------|------|
| **app/** | Єдине джерело істини: API, моделі, сервіси, telegram-боти, AI. Імпортів з `legacy` або `old_healer_logic` **немає**. |
| **legacy/** | В `.cursorignore` та `.dockerignore`. Код не копіюється в образ і не імпортується. |
| **legacy_backend_DO_NOT_USE/** | Окремий старий бекенд (інші app/, alembic, Dockerfile). У поточному репо не використовується. |

**Чому частина логіки «залишилась» в legacy:**  
Це історичний шар. Поточна архітектура свідомо перенесена в `app/`; `legacy/` залишено як довідку/бекоп і виключено з білду та пошуку.

**Рекомендація:** Якщо папки `legacy/` та `legacy_backend_DO_NOT_USE/` більше не потрібні — винести в окремий архів або репозиторій, щоб не плутати нових розробників.

---

### 1.2 Інфраструктура: PYTHONPATH і видимість модулів

| Середовище | PYTHONPATH | Видимість `app` |
|------------|------------|------------------|
| **Локально** | README: `set PYTHONPATH=.` (Windows), `export PYTHONPATH=$PYTHONPATH:.` (Unix). Потрібен для `alembic upgrade head` та `uvicorn app.main:app`. | ✅ Коректно, якщо запуск з кореня проєкту. |
| **Docker** | У поточному **Dockerfile не встановлюється** `PYTHONPATH`. `WORKDIR /app`, `COPY . .`, `CMD ["uvicorn", "app.main:app", ...]`. | ✅ Uvicorn запускається з `/app`, тому `app` — це пакет у поточній директорії; Python знаходить `app` без PYTHONPATH. |

**Висновок:** У Docker модулі видимі коректно за рахунок `WORKDIR /app`. Локально без `PYTHONPATH=.` (або без запуску з кореня) можуть падати `alembic` та імпорти типу `from app.config import ...`.

**Рекомендація:** У Dockerfile для явності можна додати `ENV PYTHONPATH=/app`. Для Cloud Run/Render — переконатися, що рабоча директорія та монтування коду відповідають очікуванням (зазвичай теж корінь з `app/`).

---

### 1.3 Frontend: зв'язок React/HTML з API, дублювання викликів і window scope

**Стек фронту:** Не React SPA, а **класичні HTML-сторінки** (Jinja2 шаблони + статичні JS).

| Файл | Призначення |
|------|-------------|
| `app/static/js/auth.js` | Експорт **одного** об’єкта: `window.HealerAuth` (токени, refresh, logout, getAuthHeaders, checkAuth). |
| `app/static/js/api.js` | Експорт **одного** об’єкта: `window.HealerAPI` (get/post/put/del), використовує `window.HealerAuth.getAuthHeaders()`. |
| `app/static/js/sidebar.js` | Експорт `window.HealerSidebar`, залежить від `window.HealerAuth`. |

**Порядок підключення (важливо):**  
У `app/static/dashboard.html` та `app/templates/dashboard/specialist.html` скрипти підключені в правильному порядку:

1. `auth.js`  
2. `api.js`  
3. `sidebar.js`  

Дублювання скриптів у цих шаблонах **не виявлено** — кожен підключений один раз. Ризик подвійних викликів API через повторне підключення `api.js` відсутній за поточним станом шаблонів.

**Потенційний ризик:** Якщо на одній сторінці підключити `api.js` двічі, `window.HealerAPI` буде перезаписано; дублікатів викликів саме через «два екземпляри API» не буде, але можлива плутанина з іншими глобальними об’єктами. Рекомендація: у всіх нових шаблонах дотримуватися єдиного порядку (auth → api → sidebar) і не підключати ці скрипти повторно.

**Підсумок:** Експорт у `window` зроблений коректно, один об’єкт на модуль; дублювання викликів через некоректний експорт не виявлено.

---

## 2. Аудит бази даних («чи прошита база?»)

### 2.1 DATABASE_URL та міграції

- **Джерело URL:** `app/config.py` → `Settings.DATABASE_URL` (за замовчуванням `sqlite:///./healer_nexus.db`).
- **Alembic:** `alembic/env.py` бере URL через `get_url()` з `app.config.settings.DATABASE_URL`; для SQLite конвертує `sqlite+aiosqlite` → `sqlite` для синхронного движка міграцій.
- **Прод:** Потрібно встановити `DATABASE_URL` у форматі PostgreSQL (наприклад `postgresql://user:pass@host/db` або через Cloud SQL Proxy).

**Важливо:** У `alembic.ini` захардкожено `sqlalchemy.url = sqlite:///./healer.db`. Фактичний URL для міграцій задається в `env.py` з `settings.DATABASE_URL`, тому пріоритет має конфіг, а не alembic.ini. Для прод обов’язково задавати `DATABASE_URL` в середовищі.

---

### 2.2 Відповідність моделей таблицям: User та Cloud SQL

**Модель** `app/models/user.py`:

- `id`, `telegram_id`, `username`, `email`, `password_hash`, `role`, `is_active`, `last_login_at`
- `balance`, `requests_left`, `total_requests`, `is_subscribed`, `subscription_end`
- Зв’язки та `TimestampMixin` (`created_at`, `updated_at`).

**Міграція** `auth_001_jwt_auth.py`:

- Додає до таблиці `users`: `email`, `password_hash`, `role`, `is_active`, `last_login_at`, робить `telegram_id` nullable, створює індекс `ix_users_email`.
- Таблиця `users` у міграціях **ніде не створюється** — лише змінюється. Це означає, що початкова схема `users` (і, ймовірно, `specialists`) могла з’явитися через `init_db()` → `Base.metadata.create_all()` або старіші скрипти.

**Розбіжність email vs username:**

- У моделі є і **email**, і **username**: email для логіну/JWT, username — окреме поле (наприклад, для відображення або Telegram username).
- У міграції auth_001 додано лише **email**; **username** у міграціях не з’являється. Якщо таблиця створювалася через `create_all()`, колонка `username` є. Якщо десь була створена тільки по міграціях без початкової міграції на створення `users`, колонки `username` може не бути.
- **Рекомендація:** Перевірити в Cloud SQL фактичний опис таблиці `users` (наприклад `\d users` в psql) і порівняти з полями в `app/models/user.py`. За потреби додати міграцію, яка створює таблицю `users` з усіма полями або додає відсутні колонки (наприклад `username`, `balance`, `requests_left` тощо).

**Виправлення в коді:** У `app/api/admin_users_router.py` для скидання пароля використовувалося поле `hashed_password`; в моделі User поле називається **password_hash**. Це виправлено: тепер використовується `user.password_hash`.

---

### 2.3 Cloud SQL Auth Proxy та пул з’єднань

**Підключення** (`app/database/connection.py`):

- Якщо задано `CLOUD_SQL_CONNECTION_NAME`, для PostgreSQL використовується Unix-сокет: `host=/cloudsql/<connection_name>` у `connect_args`.
- Движок створюється з `pool_pre_ping=True`, **pool_size** і **max_overflow** явно не задані (дефолти SQLAlchemy: pool_size=5, max_overflow=10).

**Чому може «відпадати» сесія:**

1. **Таймаути на стороні Cloud SQL / Proxy:** довгі простої з’єднань можуть закриватися. `pool_pre_ping=True` допомагає не видавати «мертві» з’єднання, але не збільшує таймаут життя на стороні сервера.
2. **Малий пул при високому навантаженні:** при багатьох конкурентних запитах можуть виникати затримки або таймаути отримання з’єднання з пулу.
3. **Рекомендація:** Для прод експериментально задати, наприклад, `pool_size=10`, `max_overflow=20` і при потребі `pool_recycle=3600` (перепідключати з’єднання раз на годину), щоб уникнути «відмерлих» сесій. Перевірити логи Cloud SQL та Cloud Run на помилки типу «connection closed» або «too many connections».

---

## 3. Виявлення «білих плям»

### 3.1 Webhook Telegram: 401 Unauthorized та pending_updates

**Поточний обробник** `app/api/telegram_webhook_router.py`:

- Приймає POST `/api/telegram/webhook`, читає JSON, викликає `process_update(data)`, у разі будь-якої помилки все одно повертає **200 і `{"ok": true}`** (щоб Telegram не ретраїв безкінечно).

**Чому можливий 401 Unauthorized:**

1. **Сервер віддає 401:** У поточному коді ендпоінт не перевіряє заголовок **X-Telegram-Bot-Api-Secret-Token**. Якщо в налаштуваннях webhook у Telegram задано Secret Token, Telegram його надсилає; якщо на бекенді є middleware або reverse proxy, що вимагає авторизацію для `/api/telegram/webhook`, вони можуть повертати 401. Тоді потрібно або виключити webhook з перевірки, або додати перевірку секретного токена в самому ендпоінті.
2. **Telegram отримує 401:** Якщо з бекенду до Telegram йдуть запити (наприклад, sendMessage) з невалідним або протермінованим токеном бота, Telegram поверне 401. Це вже зона обробки помилок у місцях, де викликається Telegram API.

**Рекомендація:** Додати опційну перевірку `X-Telegram-Bot-Api-Secret-Token` з налаштувань (наприклад `TELEGRAM_WEBHOOK_SECRET`): якщо змінна задана — порівнювати з заголовком і при невідповідності повертати 401/403, інакше не приймати оновлення. Це зменшить ризик підроблених webhook-запитів.

**pending_updates:** Обробка в поточному вигляді не залежить від `pending_updates` — ми просто приймаємо одне тіло запиту й викликаємо `process_update(data)`. Якщо Telegram надсилає кілька оновлень одним batch’ем, потрібно перевірити, чи очікується масив оновлень у `data`; за документацією Telegram зазвичай надсилає одне оновлення на один POST. Якщо виникають «залишкові» оновлення після простою, це може бути пов’язано з getUpdates vs webhook (наприклад, якщо десь тимчасово використовувався getUpdates і накопичилися pending) — окремої логіки для «pending_updates» у webhook тут немає і зазвичай не потрібна.

---

### 3.2 Auth Flow: JWT у хмарному середовищі

**Валідація** (`app/core/security.py`, `app/api/deps.py`):

- `decode_token()` використовує `jose.jwt.decode` з `algorithms=[...]`, перевіряє `exp` (термін дії) і тип токена (`access`/`refresh`). При помилці повертає `None`.
- `get_current_user` при `None` або невідповідному типі повертає **401** («Invalid or expired token»).

**Термін дії:** Береться з `settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (30) та `settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS` (7). Час у payload — UTC (`datetime.now(timezone.utc)`). У хмарному середовищі важливо, щоб системний час інстансу був синхронізований (NTP), інакше можливі хибні «expired» або навпаки затримка інвалідації.

**Секрет:** У прод обов’язково має бути встановлений `JWT_SECRET_KEY` (у `config.py` при `ENVIRONMENT=production` відсутність ключа призводить до exit(1)).

**Підсумок:** JWT валідація та термін дії реалізовані коректно; у хмарі варто переконатися в синхронізації часу та унікальності/безпеці `JWT_SECRET_KEY`.

---

### 3.3 Logging: try/except, які «ковтають» помилки без виводу

Нижче — місця, де помилки або ігноруються повністю, або логуються лише частково. Рекомендація: у критичних шляхах щонайменше логувати на рівні `logger.exception` або `logger.error`, щоб не втрачати діагностику в проді.

| Файл | Місце | Проблема |
|------|--------|----------|
| `app/services/blog_service.py` | Після `publish_post`: `except Exception: pass` при виклику `notify_post_published`. | Помилка публікації/нотифікації не видно в логах. |
| `app/services/blog_service.py` | У `publish_scheduled_posts`: внутрішній `except Exception: pass` для `notify_post_published`; зовнішній `except Exception: await self.session.rollback()` без логу. | Немає запису, чому публікація або нотифікація не вдалася; немає запису про rollback. |
| `app/services/chat_tool_executor.py` | Після `record_recommendation_viewed`: `except Exception: pass`. | Помилки аналітики рекомендацій не логуються. |
| `app/services/chat_tool_executor.py` | Після `record_details_viewed`: `except Exception: pass`. | Аналогічно. |
| `app/api/specialist_pages_router.py` | `except ValueError: pass` при парсингу slug/ID. | Можна залишити для «м’якого» fallback, але варто логувати невалідні значення (наприклад, debug). |
| `app/services/blog_publish_notifier.py` | Один з блоків: `except Exception: pass`. | Помилки нотифікації не видно. |
| `app/api/deps.py` | `get_optional_user`: `except HTTPException: return None`. | Це очікувана поведінка (опційний юзер), не «ковтання» помилки. |
| `app/core/security.py` | `decode_token`: `except JWTError: return None`. | Коректно: не розкриваємо причину невалідного токена; логувати в проді не обов’язково. |

**Рекомендація:** У всіх місцях з `except Exception: pass` у блог-сервісі, нотифікаторі та chat_tool_executor додати мінімум `logger.warning` або `logger.exception`, щоб у консолі/лог-зборі була видимість збоїв.

---

## Підсумкова таблиця дій

| Пріоритет | Що зробити |
|-----------|------------|
| Високий | Перевірити в Cloud SQL наявність і типи колонок таблиці `users` (зокрема `username`, `password_hash`, `email`) і при невідповідності додати міграцію. |
| Високий | Додати перевірку `X-Telegram-Bot-Api-Secret-Token` у webhook (опційно з env), щоб уникнути 401 і підроблених запитів. |
| Середній | У `app/database/connection.py` для прод (PostgreSQL) задати `pool_size`, `max_overflow`, за потреби `pool_recycle`. |
| Середній | Замінити «мовчазні» `except Exception: pass` у blog_service, blog_publish_notifier, chat_tool_executor на логування (warning/exception). |
| Низький | У Dockerfile додати `ENV PYTHONPATH=/app` для явності. |
| Низький | Розглянути архівування або видалення папок legacy/ та legacy_backend_DO_NOT_USE/ з репо. |

Виправлення поля пароля адміна (`hashed_password` → `password_hash`) вже внесені в `app/api/admin_users_router.py`.
