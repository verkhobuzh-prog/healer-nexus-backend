# Огляд платформи Healer Nexus (за реальним кодом)

Дата аналізу: 2025-01-31. Джерело: тільки існуючий код у `backend/app`, без припущень.

---

## 1. Що вже реалізовано

### 1.1 Підключені ендпоінти (main.py)

- **Роутери з префіксом `/api`:**
  - `chat_router` → `/api/chat` (POST)
  - `specialists_router` → `/api/specialists` (GET, GET/:id, POST, PATCH, DELETE)
  - `services_router` → `/api/services`, `/api/services/trending`
  - `health_router` → `/api/health`, `/api/health/detailed`

- **Сторінки (без API):**
  - `GET /` → index.html
  - `GET /dashboard` → dashboard.html
  - `GET /admin` → admin.html
  - `GET /tracker` → tracker.html
  - `GET /static` → статика

- **Роутер auth не підключений** — у `main.py` немає `include_router(auth_router)`. Ендпоінт `/register` з `app/api/auth.py` у застосунку недоступний.

### 1.2 Ключові модулі та стан

| Модуль | Файл | Стан |
|--------|------|------|
| **ModuleRegistry** | `app/core/module_registry.py` | Реалізований, але **жоден модуль не реєструється** у `main.py`. `get_registry()` ніде не викликається при старті. |
| **BaseModule** | `app/core/base_module.py` | Є: `health_check()`, `get_metrics()`, `safe_health_check()`, `ModuleStatus`. |
| **SpecialistsModule** | `app/modules/specialists_module.py` | Є, наслідує BaseModule, але **не зареєстрований** у поточному main.py. |
| **Health API** | `app/api/health.py` | Працює: `HealthChecker` (postgres, gemini_ai, telegram, redis), `run_all_checks()` через TaskGroup, ендпоінти `/health` та `/health/detailed`. |
| **AI-провайдер** | `app/ai/providers.py` | Один провайдер: `GeminiProvider` (google-genai), `generate_response()` з детекцією сервісу, пошуком спеціалістів у БД, генерацією тексту та smart_link. |
| **Self-reflection** | `app/ai/self_reflection.py` | `ReflectionEngine`: `detect_service()`, `classify_intent()`, `calculate_anxiety_score()`, `get_response_mode()`, `generate_smart_link()`. Ключові слова та ніші (healer, coach, teacher_math, interior_design тощо). |
| **Config** | `app/config.py` | Pydantic Settings: PROJECT_ID, GEMINI_API_KEY, DATABASE_URL, TELEGRAM_BOT_TOKEN, ADMIN_CHAT_ID, API_BASE_URL, REDIS_URL, SECRET_KEY, CRITICAL_CPU/RAM. Structured logging з RotatingFileHandler. |
| **Database** | `app/database/connection.py` | Один async engine, `async_session_maker`, `init_db()`, `get_db()`, `check_db_health()`, `emit_event()` (placeholder — тільки лог). |

### 1.3 Registry Pattern

- **Реалізація:** `ModuleRegistry` зберігає `Dict[str, BaseModule]`, методи `register()`, `get_overall_status()`, `get_all_metrics()`.
- **init_event_bus()** імпортує `app.core.event_bus.get_event_bus` — **модуля `app/core/event_bus` у проєкті немає**, тому виклик призведе до ImportError.
- **Зареєстровані модулі:** зараз **немає**. У поточному `main.py` немає викликів `get_registry()` чи `registry.register(...)`. У бекапі було `registry.register(SpecialistsModule())` — у актуальному коді це прибрано.

### 1.4 AI-провайдери

- **Використовується тільки Gemini:** `GeminiProvider` в `app/ai/providers.py`.
  - Клієнт: `genai.Client(api_key=settings.GEMINI_API_KEY, http_options={'api_version': 'v1'})`.
  - Генерація: `client.aio.models.generate_content(model="gemini-2.0-flash", ...)`.
  - Перед генерацією: `reflection_engine.detect_service()`, пошук спеціалістів у БД за `service_type`, формування smart_link.
- **Історія для Gemini:** у `_gemini_generate` використовується `msg.get("text", "")` для контенту повідомлень. У БД та в чаті історія передається з полем **`content`** (модель Message, get_history, healer_bot). Тобто **ключ не збігається** — історія в LLM може приходити порожньою.

### 1.5 Health checks

- **Де живуть:** логіка в `app/api/health.py` (клас `HealthChecker`).
- **Що перевіряють:**
  - **postgres:** `SELECT 1`, latency &lt; 50 ms → healthy, інакше degraded/down.
  - **gemini_ai:** `client.aio.models.count_tokens(model="gemini-2.0-flash-exp", contents="health_check")`.
  - **telegram:** наявність токена, GET `api.telegram.org/bot{token}/getMe` (aiohttp, timeout 5 s).
  - **redis:** підключення за `settings.REDIS_URL`, ping.
- **Ендпоінти:** `GET /api/health` (швидкий: status, timestamp, project_id), `GET /api/health/detailed` (усі чотири компоненти + overall).

Файл `app/core/health_checker.py` у **backend** відсутній; окремий детальний health_checker є в іншій частині репозиторію (не в backend/app), до main не підключений.

### 1.6 Telegram-боти

- **Що реально запускається:** `bot_runner.start_bot_process()` запускає **окремий процес** з `bot_launcher.py` (шлях: `base_path / "bot_launcher.py"`).
- **bot_launcher.py:** використовує **aiogram** (Bot, Dispatcher): команда `/start` (привітання + PROJECT_ID + Online) та **echo** усіх інших повідомлень. **HealerNexusBot і HealerAdminBot не використовуються** в цьому процесі.
- **healer_bot.py:** повноцінний бот (python-telegram-bot): меню категорій, ліміти запитів, AI через `get_ai_provider().generate_response()`, збереження повідомлень у БД. **Не запускається** main’ом — запускається лише bot_launcher з aiogram.
- **admin_bot.py:** лише коментар-заглушка; коду AdminBot немає.
- **bot.py:** клас `HealerAdminBot` з командою `/start` ("Адмін-панель активна") — також не запускається через main.

У **requirements.txt** вказано `python-telegram-bot==20.7`; **aiogram** у requirements немає — якщо в середовищі не встановлено aiogram, bot_launcher падатиме на імпорті.

---

## 2. Поточні можливості платформи

### 2.1 Користувач (веб)

- **Чат:** POST `/api/chat` — відправка повідомлення, отримання AI-відповіді та списку спеціалістів у форматі `ChatResponse` (response, detected_service, top_specialists, smart_link тощо).
- **Спеціалісти:** GET `/api/specialists` (опційно за service_type), GET `/api/specialists/{id}`, створення/оновлення/видалення через API (якщо є права доступу).
- **Послуги:** GET `/api/services` — каталог послуг з кількістю активних спеціалістів; GET `/api/services/trending` — викликає `analytics.get_trending_services(top_n=5)`, але у `SimpleAnalytics` **немає методу get_trending_services** → AttributeError при виклику.

### 2.2 Користувач (Telegram)

- **Фактично доступно:** лише бот з bot_launcher (aiogram): /start та echo. Меню категорій, AI, ліміти — у healer_bot.py, але цей бот не запускається.

### 2.3 Адмін

- **Веб:** сторінка `/admin` (admin.html) — лише віддача HTML; окремого API для адміна в коді не видно.
- **Telegram:** ADMIN_CHAT_ID використовується в healer_bot для необмежених запитів та позначки "Admin Mode"; оскільки healer_bot не запускається, це не працює. Admin bot (admin_bot.py) — заглушка.

### 2.4 Метрики та алерти

- **Метрики:** automation/monitoring.py — `collect_system_metrics()` (CPU, RAM, disk через psutil), пороги CRITICAL_CPU/CRITICAL_RAM, формування списку `alerts`. У main ця функція **не викликається** і не експонується ендпоінтом.
- **SimpleAnalytics:** лише `demand_log` в пам’яті, `log_search()`, `get_all_demand()`. Методу `get_trending_services()` немає — /api/services/trending ламається.
- **Алерти в Telegram:** у коді відправки алертів у Telegram немає; emit_event — лише лог у БД/консоль.

---

## 3. Потенціал платформи (що можна розвинути)

- **Nexus Universe (healer, eco-pulse, edu-junior, admin-market):** зараз один PROJECT_ID у config; можна ввести кілька проектів/брендів і маршрутизувати по домену або заголовку, або зберігати project_id у сесії/токені. База вже готова до одного проєкту; для multi-project потрібні окремі конфіги або мультитенантні таблиці.
- **Admin-Agent як оркестратор:** ModuleRegistry і BaseModule вже дають абстракцію модулів; можна додати "адмін-агента", який викликає `get_registry().get_overall_status()` / `get_all_metrics()`, приймає команди (наприклад, з Telegram) і керує модулями. Зараз реєстр порожній і init_event_bus ламається без event_bus — спочатку треба зареєструвати модулі та вирішити event_bus.
- **Бізнес-метрики (satisfaction_index тощо):** зараз немає збору рейтингів/відгуків. Можна додати таблиці (наприклад, feedback, ratings), викликати запис після чату/після зустрічі з спеціалістом і рахувати агрегати в SimpleAnalytics або окремому сервісі.
- **"Продаж" агентів:** немає платіжної логіки та пакетів агентів. Можна розширити модель User (balance, підписки вже частково є), додати продукти/тарифы та інтеграцію з платіжним провайдером; адмін-агент міг би повертати посилання на оплату або статус підписки.
- **Real-time оркестрація (EventBus, LISTEN/NOTIFY):** emit_event у connection.py — заглушка. ModuleRegistry передбачає event_bus (connect, listen), але модуля event_bus немає. Можна реалізувати event_bus на основі PostgreSQL LISTEN/NOTIFY або Redis Pub/Sub і підключити в init_event_bus після появи модуля.

---

## 4. Що потрібно додати/виправити (критичні покращення)

### 4.1 Критичні помилки та невідповідності

1. **Healer_bot не запускається:** main запускає bot_launcher (aiogram, echo). Щоб працювало меню + AI + ліміти — або змінити bot_launcher на запуск HealerNexusBot (healer_bot.py), або підключити aiogram до тієї ж логіки (generate_response, User/Message).
2. **Відповідь у Telegram як dict:** у healer_bot.py після `response = await ai.generate_response(...)` відправляється `f"{response}{suffix}"` — тобто рядок-представлення словника. Треба відправляти текст: `response.get("text", "")` (або врахувати ключ "response" у ChatResponse, але generate_response повертає "text").
3. **Історія для Gemini:** у providers.py в історії використовується `msg.get("text", "")`, тоді як з БД і з healer_bot приходить `content`. Треба підтримувати обидва: `msg.get("text", msg.get("content", ""))`.
4. **/api/services/trending:** викликає `analytics.get_trending_services(top_n=5)`, але у SimpleAnalytics є тільки `get_all_demand()`. Потрібно або реалізувати `get_trending_services` (на основі demand_log за період і сортування), або тимчасово повертати дані з get_all_demand.
5. **Auth:** auth.py очікує User з полями email, hashed_password, role (UserRole); у app/models/user.py є тільки telegram_id, username, balance, requests_left, is_subscribed, subscription_end. Модель User не підходить для register. Потрібно або окрема модель (наприклад, WebUser) для веб-реєстрації, або розширити User і додати міграції; також потрібно підключити auth_router у main.py, якщо веб-реєстрація потрібна.
6. **EventBus:** module_registry.init_event_bus() імпортує app.core.event_bus — модуля немає. Або створити event_bus (наприклад, на Redis/Postgres), або прибрати/заглушити виклик init_event_bus, щоб не було ImportError при першому виклику.

### 4.2 Production: logging, tests, rate limiting, auth

- **Logging:** уже є (config.py): RotatingFileHandler, StructuredLogFilter, project_id/component. Можна додати JSON-формат для збору в файли/стек.
- **Tests:** у проєкті тестів не видно — додати pytest, тести на /api/health, /api/chat, CRUD спеціалістів, health_check модулів.
- **Rate limiting:** немає; додати middleware або обмеження по IP/токену для /api/chat та публічних ендпоінтів.
- **Auth:** веб-авторизація не реалізована (auth не підключений, модель User не для веб). Для production потрібно визначитися: JWT, session, або тільки Telegram — і реалізувати перевірку на захищених ендпоінтах.

### 4.3 Multi-project: project_id, shared DB, моніторинг

- **project_id:** вже є в settings (PROJECT_ID) та в логах; у health відповіді повертається project_id. Для кількох проектів потрібні окремі конфіги або один DB з полем project_id у ключових таблицях.
- **Shared DB:** одна DATABASE_URL; для розділення даних між проєктами — додати project_id до users, messages, specialists тощо і фільтрувати запити.
- **Cross-project моніторинг:** get_registry().get_overall_status() можна викликати з одного місця; зараз реєстр порожній — спочатку зареєструвати модулі (наприклад, SpecialistsModule) у lifespan main.

### 4.4 Admin-Agent

- Зараз лише ідея: окремий бот або команди в існуючому боті. Потрібна реалізація: обробник команд (наприклад, /status, /metrics), виклик get_registry().get_overall_status() та get_all_metrics(), відправка результатів у ADMIN_CHAT_ID. Можна використати bot_launcher або healer_bot після того, як буде визначено, який бот реально запускається.

### 4.5 Пріоритетний список на 3–7 днів

| Пріоритет | Задача | Дія |
|-----------|--------|-----|
| P0 | Користувач у Telegram бачить AI, а не echo | Підключити healer_bot (або його логіку) у bot_launcher замість простого echo. |
| P0 | Відповідь у Telegram — текст, не dict | У healer_bot використовувати `response.get("text", "")` для reply. |
| P0 | Історія в AI не порожня | У providers.py при формуванні contents брати `msg.get("text", msg.get("content", ""))`. |
| P1 | /api/services/trending не падає | Додати get_trending_services у SimpleAnalytics або замінити ендпоінт на get_all_demand. |
| P1 | Реєстр модулів не порожній | У lifespan main викликати get_registry() і register(SpecialistsModule()); при потребі — інші модулі. |
| P1 | EventBus не ламає старт | Або створити app/core/event_bus (наприклад, Redis), або не викликати init_event_bus / обгорнути в try та заглушку. |
| P2 | Auth узгоджений з моделлю | Визначити одну модель користувача (веб vs Telegram), додати поля або окрему модель; підключити auth_router у main. |
| P2 | Моніторинг доступний | Викликати collect_system_metrics по таймеру або ендпоінту; за бажанням — відправка алертів у Telegram при alerts. |
| P3 | Rate limit, тести, документація | Додати обмеження запитів, базові тести, оновити README з актуальним станом. |

---

*Документ згенеровано на основі стану репозиторію backend; будь-які зміни в коді потребують оновлення огляду.*
