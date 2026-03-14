# 🤖 HEALER NEXUS — AI AGENTS INTEGRATION GUIDE
# Версія: 1.0 | Дата: 13 березня 2026
# Для: Ігор Верхобуж | Інструмент: Cursor AI

---

## 📦 НОВІ ФАЙЛИ (скопіювати в проект)

```
app/
├── agents/                          ← НОВА ПАПКА
│   ├── __init__.py                  ← Експорт agent_manager
│   ├── base_agent.py                ← Базовий клас агента
│   ├── health_check_agent.py        ← Моніторинг здоров'я API + БД
│   ├── security_agent.py            ← Безпека: brute-force, аномалії
│   ├── bug_scanner_agent.py         ← Сканер відомих багів (B-02...B-09)
│   ├── qa_tester_agent.py           ← Smoke-тести API endpoints
│   ├── advisor_agent.py             ← AI рекомендації через Gemini
│   └── agent_manager.py             ← Оркестратор усіх агентів
├── models/
│   └── agent_config.py              ← НОВИЙ: моделі AgentConfig + AgentLog
└── api/
    └── agent_router.py              ← НОВИЙ: API endpoints для управління
```

---

## 🔧 ЗМІНИ В ІСНУЮЧИХ ФАЙЛАХ

### 1. app/main.py — додати імпорт роутера + startup/shutdown

Знайти секцію імпорту роутерів і ДОДАТИ:
```python
from app.api.agent_router import router as agent_router
```

Знайти секцію `app.include_router(...)` і ДОДАТИ в кінець:
```python
app.include_router(agent_router)
```

Знайти функцію `startup()` і ДОДАТИ перед `logger.info("Healer Nexus started")`:
```python
    # AI Agents
    from app.agents.agent_manager import agent_manager
    await agent_manager.start_all()
```

Знайти функцію `shutdown()` і ДОДАТИ:
```python
    # Stop AI Agents
    from app.agents.agent_manager import agent_manager
    await agent_manager.stop_all()
```

### 2. app/database/connection.py — додати імпорт моделей

Знайти де імпортуються моделі (де є `import ... AgentAuditLog`) і ДОДАТИ:
```python
from app.models.agent_config import AgentConfig, AgentLog
```

**ТАКОЖ** — потрібен `async_session_factory`. Якщо його ще немає, додати:
```python
from sqlalchemy.ext.asyncio import async_sessionmaker

# Після створення engine:
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
```

### 3. app/config.py — додати налаштування для Telegram сповіщень

Додати в клас Settings:
```python
    # Telegram Agent Notifications
    TELEGRAM_ADMIN_CHAT_ID: str | None = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
```

### 4. requirements.txt — додати httpx (якщо немає)

Перевірити чи є `httpx` в requirements.txt. Якщо немає:
```
httpx>=0.25.0
```

---

## 🧪 ТЕСТУВАННЯ (локально)

### Крок 1: Перевірити імпорт
```powershell
python -c "from app.agents.agent_manager import agent_manager; print('Agents OK')"
```

### Крок 2: Запустити сервер
```powershell
uvicorn app.main:app --reload
```

В логах має з'явитись:
```
🤖 Agent Manager: starting all agents...
  ✅ health_check — started
  ✅ security_watch — started
  ✅ bug_scanner — started
  ✅ qa_tester — started
  ✅ advisor — started
🤖 Agent Manager: 5 agents initialized
```

### Крок 3: Перевірити API
```powershell
# Логін як admin
$login = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" -Method Post -ContentType "application/json" -Body '{"email":"verkhobuzh@gmail.com","password":"Igor_Nexus_2026!"}'

# Статус агентів
Invoke-RestMethod -Uri "http://localhost:8000/api/agents/status" -Headers @{"Authorization"="Bearer $($login.access_token)"}

# Увімкнути health_check
Invoke-RestMethod -Uri "http://localhost:8000/api/agents/health_check/enable" -Method Post -Headers @{"Authorization"="Bearer $($login.access_token)"}

# Ручний запуск bug_scanner
Invoke-RestMethod -Uri "http://localhost:8000/api/agents/bug_scanner/run" -Method Post -Headers @{"Authorization"="Bearer $($login.access_token)"}

# Переглянути логи
Invoke-RestMethod -Uri "http://localhost:8000/api/agents/logs?limit=20" -Headers @{"Authorization"="Bearer $($login.access_token)"}
```

---

## 📱 TELEGRAM СПОВІЩЕННЯ

Щоб агенти слали алерти в Telegram:

1. Дізнатись свій chat_id (написати @userinfobot в Telegram)
2. Додати змінну середовища:
   - Локально: в .env файл `TELEGRAM_ADMIN_CHAT_ID=ваш_chat_id`
   - Production: в Cloud Run ENV

Агенти використовують існуючий @kozubalihor_bot для відправки.

---

## ⚙️ КОНФІГУРАЦІЯ АГЕНТІВ

Кожен агент контролюється через таблицю `agent_configs` в БД.
При першому запуску конфіги створюються автоматично (всі disabled).

### Увімкнення через API:
```
POST /api/agents/health_check/enable
POST /api/agents/security_watch/enable
POST /api/agents/bug_scanner/enable
POST /api/agents/qa_tester/enable
POST /api/agents/advisor/enable
```

### Зміна інтервалу:
```
PUT /api/agents/health_check/config
Body: {"interval_seconds": 60}
```

### Зміна рівня сповіщень:
```
PUT /api/agents/security_watch/config
Body: {"notify_on_severity": "error"}
```

---

## 🏗 АРХІТЕКТУРА АГЕНТІВ

```
┌─────────────────────────────────────────────┐
│              Agent Manager                   │
│  (start_all / stop_all / status / run_once) │
├─────────────┬───────────┬───────────────────┤
│HealthCheck  │ Security  │ BugScanner        │
│ (2 хв)      │ (3 хв)    │ (10 хв)           │
├─────────────┼───────────┼───────────────────┤
│ QATester    │ Advisor   │ [Future agents]    │
│ (15 хв)     │ (24 год)  │                    │
└──────┬──────┴─────┬─────┴───────────────────┘
       │            │
       ▼            ▼
  agent_logs    agent_configs
  (PostgreSQL)  (PostgreSQL)
       │
       ▼
  Telegram Bot
  (@kozubalihor_bot)
```

Кожен агент:
1. Читає свій config з agent_configs
2. Якщо is_enabled=true → виконує execute()
3. Записує результат в agent_logs
4. Якщо severity >= notify_on_severity → шле Telegram

---

## 🔜 НАСТУПНІ АГЕНТИ (Фаза 2)

Після стабілізації Фази 1, можна додати:

- **PerformanceAgent** — моніторинг часу відповіді кожного endpoint
- **SEOAgent** — перевірка meta-тегів, sitemap, robots.txt
- **ContentAgent** — автогенерація контенту через Gemini
- **BackupAgent** — автоматичні бекапи БД
- **CleanupAgent** — очистка старих логів, прострочених токенів

Додавання нового агента:
1. Створити файл в `app/agents/new_agent.py`
2. Успадкувати від `BaseAgent`
3. Реалізувати `execute()`
4. Додати в `agent_manager.py` → `self._agents`

---

*Створено: 13 березня 2026 | Claude AI для Healer Nexus*
