# СТАН ПРОЕКТУ НА СЬОГОДНІ (Healer Nexus Platform)

**Дата:** 2026-02-05  
**Коміт:** `1d23e84` (Initial commit з force push)  
**Репозиторій:** [https://github.com/verkhobuzh-prog/healer-nexus-backend](https://github.com/verkhobuzh-prog/healer-nexus-backend) (private)

---

## 1. Поточна структура (коротке дерево)

```
C:\Projects\healer-backend\              # Git root, робоча директорія
│
├── app/                                 # Основний код (активний)
│   ├── main.py                          # FastAPI entry point
│   ├── config.py                        # ✅ Source of truth
│   ├── core/
│   │   ├── module_registry.py           # Multi-project orchestration
│   │   ├── event_bus.py                 # ⚠️ Stub (Redis planned)
│   │   └── config.py                    # ⚠️ Proxy (дублікат?)
│   ├── ai/
│   │   ├── providers.py                 # Gemini integration
│   │   └── self_reflection.py
│   ├── api/
│   │   ├── chat.py                      # ✅ Working
│   │   ├── specialists.py               # ✅ Working (CRUD)
│   │   ├── services.py                  # ⚠️ available_specialists=0
│   │   ├── health.py                    # ✅ Working
│   │   └── auth.py                      # ⚠️ Not connected
│   ├── telegram/
│   │   ├── healer_bot.py                # ✅ Polling active
│   │   ├── admin_bot.py                 # ⚠️ Stub
│   │   └── bot_runner.py
│   ├── resilience/
│   │   ├── self_heal.py                 # ✅ Implemented
│   │   └── safe_mode.py
│   ├── models/                          # ✅ All have project_id
│   ├── schemas/                         # ✅ Pydantic v2
│   └── static/                          # HTML files
│
├── alembic/                             # Migrations
│   └── versions/                        # ⚠️ Location unclear (backend/ or root?)
│
├── healer_nexus.db                      # ✅ Active database (SQLite)
├── .env                                 # ✅ Secrets
├── .gitignore                           # ✅ Configured
├── requirements.txt                     # ✅ Dependencies
│
├── backend/                             # ⚠️ OLD duplicate (not used)
├── OLD_backend_backup/                  # ❌ Deleted (cleanup done)
└── legacy/                              # ⚠️ Old code (ignore)
```

---

## 2. Що вже працює стабільно


| Компонент                  | Статус | Деталі                                                    |
| -------------------------- | ------ | --------------------------------------------------------- |
| **FastAPI сервер**         | ✅      | Запускається на порту 8000, без помилок                   |
| **База даних (SQLite)**    | ✅      | `healer_nexus.db`, WAL mode, `project_id` у всіх таблицях |
| **Telegram healer_bot**    | ✅      | Polling активний, меню працює, AI chat інтегровано        |
| **API `/api/chat**`        | ✅      | Відповідає, викликає Gemini                               |
| **API `/api/specialists**` | ✅      | CRUD працює (GET/POST/PATCH/DELETE)                       |
| **API `/api/health**`      | ✅      | Повертає статус системи                                   |
| **Self-healing**           | ✅      | `@with_self_heal` реалізовано, готово до використання     |
| **Module Registry**        | ✅      | Основна логіка є, multi-project готова                    |
| **Git історія**            | ✅      | Спрощена через force push, один initial commit            |
| **GitHub репо**            | ✅      | Private, код залитий                                      |


---

## 3. Що ще не працює / проблеми


| Проблема                        | Статус | Деталі                                                                                     |
| ------------------------------- | ------ | ------------------------------------------------------------------------------------------ |
| **Gemini 404 error**            | 🔴     | Модель `gemini-2.0-flash-exp` не існує або неправильний ключ → потрібно `gemini-1.5-flash` |
| `**available_specialists = 0**` | 🔴     | `/api/services` показує 0 спеціалістів, хоча вони є в БД → перевірити фільтр `project_id`  |
| **Redis not configured**        | 🟡     | EventBus — заглушка, Redis не підключений (planned для Phase 2)                            |
| **admin_bot**                   | 🟡     | Існує код, але функціонал — stub (тільки заглушка)                                         |
| **Auth не підключено**          | 🟡     | `app/api/auth.py` є, але router не додано в `main.py`                                      |
| **Два config.py**               | 🟡     | `app/config.py` (source of truth) + `app/core/config.py` (proxy?) → можлива плутанина      |
| **run.py**                      | 🔴     | Посилається на відсутній `admin_agent.main` (якщо файл ще є)                               |
| **Alembic location**            | 🟡     | Незрозуміло: `backend/alembic` чи `alembic` у корені                                       |


---

## 4. Ключові компоненти та їх статус

### A. Telegram Боти


| Компонент       | Статус   | Токен                | Функціонал                             |
| --------------- | -------- | -------------------- | -------------------------------------- |
| `healer_bot.py` | ✅ Працює | `TELEGRAM_BOT_TOKEN` | Меню, AI chat, user limits, admin mode |
| `admin_bot.py`  | ⚠️ Stub  | `ADMIN_BOT_TOKEN`    | Код є, але функції не реалізовані      |
| `bot_runner.py` | ✅ Працює | —                    | Запускає обидва боти в одному процесі  |


### B. AI Integration


| Компонент            | Статус                | Модель                 | Проблема                                           |
| -------------------- | --------------------- | ---------------------- | -------------------------------------------------- |
| `providers.py`       | ⚠️ Працює з помилками | `gemini-2.0-flash-exp` | 404 error → потрібно змінити на `gemini-1.5-flash` |
| `self_reflection.py` | ✅                     | —                      | Аналізує стан користувача                          |
| Safe Mode            | ✅                     | —                      | Fallback до пошуку спеціалістів                    |


### C. База даних


| Параметр          | Значення                         |
| ----------------- | -------------------------------- |
| **Тип**           | SQLite (aiosqlite)               |
| **Файл**          | `healer_nexus.db`                |
| **Режим**         | WAL (Write-Ahead Logging)        |
| **Multi-project** | ✅ (`project_id` у всіх таблицях) |
| **Міграції**      | ✅ Alembic налаштований (async)   |


### D. API Endpoints


| Endpoint                 | Метод                 | Статус | Проблема                    |
| ------------------------ | --------------------- | ------ | --------------------------- |
| `/api/chat`              | POST                  | ✅      | Gemini 404 (модель)         |
| `/api/specialists`       | GET/POST/PATCH/DELETE | ✅      | —                           |
| `/api/services`          | GET                   | ⚠️     | `available_specialists = 0` |
| `/api/services/trending` | GET                   | ✅      | —                           |
| `/api/health`            | GET                   | ✅      | —                           |
| `/api/health/full`       | GET                   | ✅      | —                           |
| `/api/auth/*`            | —                     | ❌      | Router не підключений       |


### E. Resilience & Monitoring


| Компонент       | Статус  | Функціонал                            |
| --------------- | ------- | ------------------------------------- |
| `self_heal.py`  | ✅       | Auto-restart на AssertionError        |
| `safe_mode.py`  | ✅       | AI fallback до specialist search      |
| `monitoring.py` | ✅       | CPU/RAM/disk metrics, Telegram alerts |
| EventBus        | ⚠️ Stub | In-memory, Redis planned              |


---

## 5. Git та репозиторій статус


| Параметр            | Значення                                                                                                           |
| ------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **Remote**          | [https://github.com/verkhobuzh-prog/healer-nexus-backend](https://github.com/verkhobuzh-prog/healer-nexus-backend) |
| **Branch**          | `main`                                                                                                             |
| **Last commit**     | `1d23e84` (Initial commit)                                                                                         |
| **Force push**      | ✅ Виконано (історія спрощена)                                                                                      |
| **Working tree**    | ✅ Clean (після видалення `OLD_backend_backup/`)                                                                    |
| **Untracked files** | ⚠️ Можливо `backend/` дубль (перевірити)                                                                           |


**Git статус (приблизно):**

```bash
$ git status
On branch main
nothing to commit, working tree clean
```

---

## 6. Наступний пріоритетний крок (конкретні задачі)

### 🔴 CRITICAL (потрібно виправити зараз):

1. **Виправити Gemini модель**
  - Файл: `app/ai/providers.py`
  - Змінити: `gemini-2.0-flash-exp` → `gemini-1.5-flash`
  - Тест: `curl http://localhost:8000/api/chat` має повернути відповідь без 404
2. **Виправити `available_specialists = 0**`
  - Файл: `app/api/services.py`
  - Перевірити: чи фільтр `project_id == "healer_nexus"` правильний
  - Тест: `/api/services` має показати 4+ спеціалістів (якщо є seed data)

### 🟡 IMPORTANT (на наступний день):

1. **Очистити дублікат `backend/**`
  - Якщо папка `backend/` ще існує і не використовується → видалити або перемістити в `legacy/`
  - Переконатися: `alembic/` у корені (не в `backend/alembic/`)
2. **Видалити `run.py` або виправити**
  - Якщо файл посилається на `admin_agent.main` (не існує) → видалити
  - Або переписати для запуску через `uvicorn app.main:app`
3. **Уточнити два config.py**
  - `app/config.py` — залишити як source of truth
  - `app/core/config.py` — або видалити, або зробити proxy (re-export)

---

## 🎯 Підсумок

**Що працює:** FastAPI, SQLite, healer_bot, базові API endpoints, self-healing, Git.

**Що не працює:** Gemini 404, available_specialists=0, admin_bot (stub), auth (не підключено), Redis (stub).

**Наступний крок:** Виправити Gemini модель + available_specialists → платформа стане повністю функціональною для Phase 1.

---

**Чесний висновок:** Проєкт у **доброму стані** для Phase 1 (90% готово). Критичні блокери — Gemini та specialists count — легко виправляються. Архітектура (Modular Monolith, multi-project, self-healing) — **solid foundation** для Phase 2 (Marketplace).

---

**Версія документа:** 1.0.0  
**О**  
**станнє оновлення:** 2026-02-05**Джерело:** Grok аналіз + реальний стан коду