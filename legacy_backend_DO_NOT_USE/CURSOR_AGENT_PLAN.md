# Технічний план для Cursor Agent — Healer Nexus

Скопіюй цей блок у Cursor і виконуй кроки по черзі. Дотримуйся `.cursorrules`, Python 3.13, async-first, PEP 695.

---

## 1. Self-Healing & Monitoring (Запобігання падінню)

### 1.1 HealthCheck ендпоінт (вже реалізовано частково)

- **Файл:** `app/api/health.py`
- **Що є:** `GET /api/health` (швидкий), `GET /api/health/detailed` (Postgres, Gemini, Telegram, Redis з затримкою), `GET /api/health/full` (компоненти + статус модулів з реєстру).
- **Що перевіряти:** Cursor має переконатися, що:
  - У відповіді `full` є поля `database.latency_ms`, `google_ai.status` та `google_ai.latency_ms`.
  - Якщо їх немає — додай або прив’яжи до існуючого `detailed`/`full`.
- **Пороги:** DB: healthy &lt; 50 ms, degraded ≥ 50 ms; Gemini: healthy при успішному `count_tokens`, degraded при помилці.

### 1.2 Автоматичний рестарт при AssertionError (Python 3.13)

- **Файл:** `app/resilience/self_heal.py`
- **Що є:** `register_restart_handler()`, `run_restart_handlers()`, `with_self_heal(coro)` — при `AssertionError` викликаються зареєстровані async-колбеки і виняток пробросується далі.
- **Що зробити:**
  1. У lifespan у `main.py` зареєструй один handler, наприклад: переініціалізація AI-провайдера (створення нового клієнта) або лог "restart requested".
  2. Обгорни критичні виклики (наприклад, `generate_response` або один із health checks) у `with_self_heal(coro)` там, де це має сенс — щоб при `AssertionError` спочатку виконались restart handlers, потім виняток йшов далі.
- **Важливо:** У Python 3.13 `AssertionError` не змінився; механізм універсальний.

---

## 2. Admin Agent (Multi-Project Vision)

### 2.1 Концепція "Центрального Адмін-Агента"

- Один оркестратор бачить стан **цього** проєкту + N майбутніх (наприклад, healer_nexus, eco-pulse, edu-junior, admin-market).
- Джерела даних: **спільна шина** (EventBus) або **Shared Database** з таблицею `project_health` (project_id, status, latency_ms, updated_at).

### 2.2 Зміни в `app/core/module_registry.py` (вже закладені)

- **Що є:**
  - `ModuleRegistry(project_id)` — реєстр має `global_project_id`.
  - `register_child_project(project_id)` — реєстрація ID дочірнього проєкту.
  - `get_child_project_ids()` — список дочірніх ID.
  - `get_all_projects_status()` — повертає `this_project_id`, `this` (поточний статус модулів), `children: { project_id: { status, source } }`. Для children зараз placeholder `status: "unknown"`, `source: "placeholder"`.
- **Що зробити Cursor:**
  1. У lifespan після `register_all()` викликати `get_registry().register_child_project("eco-pulse")`, `register_child_project("edu-junior")`, `register_child_project("admin-market")` — якщо ці проєкти мають бути видимі для Admin-Agent (або читати список з config/settings).
  2. Реалізувати заповнення `children` у `get_all_projects_status()`:
     - **Варіант A (Shared DB):** якщо є таблиця `project_health`, робити `SELECT project_id, status, latency_ms FROM project_health WHERE project_id IN (child_ids)` і підставляти в `result["children"]`.
     - **Варіант B (EventBus):** підписка на події від дочірніх проєктів і кешування останнього статусу в пам’яті; у `get_all_projects_status()` повертати цей кеш для `children`.
  3. Додати ендпоінт для Admin-Agent, наприклад `GET /api/admin/projects/status`, що повертає `get_registry().get_all_projects_status()` (захистити по API-ключу або ADMIN_CHAT_ID, якщо потрібно).

---

## 3. Код-рев’ю для Cursor

### 3.1 `app/ai/self_reflection.py` (Python 3.13, типи)

- **Що зроблено:** Додано явні типи: `keyword_weights: dict[str, float]`, `service_scores: dict[str, float]`, `anxiety_words: dict[str, float]`, `max_score: float`, `__init__ -> None`. Додано `from __future__ import annotations`.
- **На що звернути увагу:**
  - Усі методи мають явні return-типи (`Tuple[str, float]`, `UserIntent`, `float`, `ResponseMode`, `str`).
  - У Python 3.13 можна використовувати PEP 695 type alias у майбутньому, наприклад `type ServiceScores = dict[str, float]` — опційно для читабельності.
  - Уникнути `dict` без параметризації (замість `dict` краще `dict[str, float]`), щоб уникнути конфліктів типів у 3.13.

### 3.2 Сумісність httpx та python-telegram-bot

- **Що зроблено:** У `requirements.txt` зафіксовано діапазон: `httpx>=0.24,<0.28`, щоб уникнути конфлікту з python-telegram-bot 20.7.
- **Що зробити Cursor:**
  1. Перевірити, що після `pip install -r requirements.txt` немає помилок і що бот запускається.
  2. Якщо використовується `pyproject.toml` з dependency groups (optional dependencies), додати групу, наприклад:
     - `[project.optional-dependencies]`
     - `telegram = ["python-telegram-bot==20.7", "httpx>=0.24,<0.28"]`
     - Встановлення: `pip install -e ".[telegram]"`.
  3. Якщо конфлікт залишається — перевірити changelog python-telegram-bot 20.x на рекомендовану версію httpx і підправити діапазон у requirements.txt.

---

## 4. Чеклист для Cursor Agent

- [ ] Перевірити, що `GET /api/health/full` повертає `database.latency_ms`, `google_ai.status`, `google_ai.latency_ms` та `modules`.
- [ ] У `main.py` lifespan зареєструвати хоча б один restart handler у `self_heal` і (опційно) обгорнути один критичний виклик у `with_self_heal`.
- [ ] У `module_registry`: викликати `register_child_project(...)` для майбутніх проєктів або з конфігу; реалізувати заповнення `children` у `get_all_projects_status()` (Shared DB або EventBus).
- [ ] Додати `GET /api/admin/projects/status` (з захистом за бажанням), що використовує `get_all_projects_status()`.
- [ ] Перевірити `self_reflection.py`: усі dict/return типи явні, без конфліктів для Python 3.13.
- [ ] Перевірити встановлення залежностей: `httpx>=0.24,<0.28` + `python-telegram-bot==20.7` без конфліктів; за потреби додати optional dependency group у pyproject.toml.

---

*Після виконання цих кроків платформа матиме повноцінний HealthCheck (включно з затримкою БД та Google AI), механізм self-healing при AssertionError, реєстр готовий до ролі "материнського" для кількох проєктів, та узгоджені типи й залежності для Python 3.13.*
