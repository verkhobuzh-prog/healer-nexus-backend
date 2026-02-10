# Session Manager — Центр керування розмовами з Claude

**Мета:** Розбити роботу над Healer Nexus на модульні сесії, кожна з чітким scope та маркерами переходу.

---

## 🗂️ Принцип розбивки

**Проблема:** Одна розмова з Claude має обмежений контекст (~200K токенів). При складній платформі контекст переповнюється.

**Рішення:** Розбити роботу на **тематичні сесії**, кожна з маркером стану.

---

## 📋 Структура сесії

### Початок сесії (Session Start):
```markdown
# 🔖 SESSION START: [Module Name]

## Context from previous session:
[Paste previous session marker here]

## Current goal:
- [Specific task 1]
- [Specific task 2]

## Expected outcome:
[What should be working after this session]
```

### Кінець сесії (Session End):
```markdown
# 🔖 SESSION END: [Module Name]

## ✅ Completed:
- [x] Task 1
- [x] Task 2

## ⚠️ Pending:
- [ ] Task 3 (for next session)

## 📊 Current state:
- Database: [migrations applied? seeded?]
- Server: [running? errors?]
- Tests: [passed? failed?]

## 🔧 Files modified:
- app/path/to/file1.py
- app/path/to/file2.py

## 🚀 Next session should:
1. [Continue with task 3]
2. [Start Module X]

## ❓ Open questions:
- [Any blockers or decisions needed]

## 📝 Copy this marker to next session ↓
```

---

## 🎯 Модулі платформи (розбивка по сесіям)

### 🟢 MODULE 1: Core Infrastructure
**Status:** 95% ✅  
**Sessions:** 2-3 (майже готово)

**Sub-modules:**
1. **Database + Alembic** (1 session)
   - SQLite + aiosqlite
   - Migrations (project_id column)
   - Seed data

2. **Config + Logging** (1 session)
   - app/config.py (source of truth)
   - Structured logging
   - .env loading

3. **EventBus Stub → Redis** (1 session, Phase 2)
   - Replace stub with Redis Pub/Sub
   - Integration tests

---

### 🟡 MODULE 2: AI Provider
**Status:** 70% ⚠️  
**Sessions:** 2-3

**Sub-modules:**
1. **Gemini Integration** (1 session) — **URGENT**
   - Fix: model gemini-2.0-flash-exp → gemini-1.5-flash
   - Test: /api/chat returns valid response

2. **Safe Mode Fallback** (1 session)
   - Specialist search when AI fails
   - Test: 404 error → returns specialists

3. **Model Fallback Chain** (1 session, Phase 2)
   - Try gemini-1.5-flash → gemini-1.5-pro → safe mode
   - Retry logic with exponential backoff

---

### 🟡 MODULE 3: Telegram Bot
**Status:** 60% ⚠️  
**Sessions:** 2-3

**Sub-modules:**
1. **healer_bot Polish** (1 session)
   - Add timeouts (connect_timeout, read_timeout)
   - Inline keyboards for specialist selection
   - Test: no TimedOut errors

2. **admin_bot Implementation** (1 session)
   - /system_status command
   - /metrics command
   - Integration with module_registry

3. **Subscription Flow** (1 session, Phase 2)
   - /subscribe command
   - Payment integration (Stripe/LiqPay)

---

### 🔴 MODULE 4: Authentication
**Status:** 0% (код є, не підключено)  
**Sessions:** 1-2

**Sub-modules:**
1. **Enable Auth Router** (1 session)
   - Add auth_router to main.py
   - Test: /api/auth/register, /api/auth/login

2. **Protect Endpoints** (1 session)
   - Add Depends(get_current_user) to specialists, services
   - Test: 401 Unauthorized without token

---

### 🔴 MODULE 5: API Endpoints
**Status:** 40% ⚠️  
**Sessions:** 2-3

**Sub-modules:**
1. **Fix available_specialists** (1 session) — **URGENT**
   - Debug: why /api/services shows 0 specialists
   - Fix: project_id filter or seed data

2. **Schema Compatibility** (1 session)
   - specialty ↔ specialization alias
   - Backward compatibility tests

3. **Rate Limiting** (1 session, Phase 2)
   - slowapi or custom decorator
   - Per-user limits

---

### 🔴 MODULE 6: Admin Agent
**Status:** 10% (registry готовий)  
**Sessions:** 2-3 (Phase 2)

**Sub-modules:**
1. **/api/admin/projects/status** (1 session)
   - Endpoint for multi-project health
   - Integration with module_registry

2. **Child Project Registration** (1 session)
   - register_child_project("eco_pulse")
   - Cross-project event routing

3. **Admin Dashboard** (1 session)
   - Real-time metrics
   - Top Active Agents (Phase 2: Marketplace)

---

### 🔴 MODULE 7: Monitoring
**Status:** 50% ✅  
**Sessions:** 1-2

**Sub-modules:**
1. **Application Metrics** (1 session)
   - Requests/sec, latency p50/p95/p99
   - Prometheus exporter (optional)

2. **Slow Query Logging** (1 session)
   - SQLAlchemy event listeners
   - Alert on queries >1s

---

### 🔴 MODULE 8: Business Logic
**Status:** 20% ⚠️  
**Sessions:** 2-3 (Phase 2)

**Sub-modules:**
1. **Subscription System** (1 session)
   - User.subscription_tier, User.balance
   - Payment webhooks

2. **satisfaction_index** (1 session)
   - Calculate from self_reflection
   - Store in Message table

3. **Revenue Tracking** (1 session)
   - Usage logs per agent (Phase 2: Marketplace)
   - Billing reports

---

### 🔴 MODULE 9: Deployment
**Status:** 0%  
**Sessions:** 2-3 (Phase 2-3)

**Sub-modules:**
1. **Docker Compose** (1 session)
   - PostgreSQL + Redis + FastAPI
   - Production .env template

2. **CI/CD** (1 session)
   - GitHub Actions
   - Automated tests

3. **Blue-Green Deployment** (1 session, Phase 3)
   - Canary rollouts via Registry
   - Health checks before switchover

---

## 🎯 Рекомендований порядок сесій

### **Зараз (Phase 1 завершення):**
1. ✅ **SESSION 1:** Core Infrastructure (done)
2. 🔴 **SESSION 2:** Fix AI Provider (Gemini model + available_specialists) — **URGENT**
3. 🟡 **SESSION 3:** Telegram Bot Polish (timeouts, inline keyboards)
4. 🟡 **SESSION 4:** Enable Authentication
5. 🟡 **SESSION 5:** API Endpoints (schema compatibility, rate limiting)

### **Після Phase 1 (Phase 2: Marketplace):**
6. 🔴 **SESSION 6:** Admin Agent API (/api/admin/projects/status)
7. 🔴 **SESSION 7:** EventBus → Redis
8. 🔴 **SESSION 8:** Agent Factory + Tenant Manager
9. 🔴 **SESSION 9:** Template Engine (roles from DB)
10. 🔴 **SESSION 10:** Usage Tracking (billing)

### **Phase 3 (Scaling):**
11. 🔴 **SESSION 11:** Application Metrics + Dashboard
12. 🔴 **SESSION 12:** Docker Compose + CI/CD
13. 🔴 **SESSION 13:** Blue-Green Deployment

---

## 📝 Шаблон маркера для копіювання

### Початок нової сесії:

```markdown
# 🔖 SESSION START: [MODULE_NAME]

## Previous session recap:
[Copy previous session marker here]

## Goals for this session:
1. [Task 1]
2. [Task 2]

## Expected outcome:
- [What should work after this session]

## Files to modify:
- app/path/to/file1.py
- app/path/to/file2.py

---

[YOUR WORK HERE]

---
```

### Кінець сесії (копіюй це в наступну розмову):

```markdown
# 🔖 SESSION END: [MODULE_NAME]

## ✅ Completed:
- [x] Task 1
- [x] Task 2

## ⚠️ Pending:
- [ ] Task 3 (blocked by X)

## 📊 Current state:
- **Database:** [healer_nexus.db, migrations applied, 4 specialists seeded]
- **Server:** [running on :8000, no errors]
- **Tests:** [/api/chat returns 200, Gemini works]
- **Blockers:** [None / Redis not configured]

## 🔧 Files modified:
- app/ai/providers.py (changed model to gemini-1.5-flash)
- app/api/services.py (fixed available_specialists query)

## 🚀 Next session:
**MODULE:** [Next module name]
**Tasks:**
1. [Continue with task 3]
2. [Start new feature X]

**Preparation:**
- [ ] Review [specific file]
- [ ] Test [specific endpoint]

## ❓ Open questions:
- Should we use Redis or PostgreSQL LISTEN/NOTIFY for EventBus?
- When to start Phase 2 (Marketplace)?

## 📋 Verification commands:
```bash
# Test Gemini
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","user_id":"test"}'

# Check specialists
curl http://localhost:8000/api/services
```

## 📝 Copy below to next session ↓
---

# 🔖 SESSION [NUMBER]: [MODULE_NAME]

[Paste this entire section in next conversation with Claude]
```

---

## 🎓 Поради для ефективних сесій

### 1. **Одна сесія = один модуль**
- Не змішуй AI Provider з Telegram Bot в одній сесії
- Фокус на одній проблемі

### 2. **Завжди копіюй маркер**
- Початок нової розмови: вставляй SESSION END з попередньої
- Claude одразу розуміє контекст

### 3. **Тестуй в кінці сесії**
- Перевір, що все працює
- Запиши verification commands у маркер

### 4. **Документуй рішення**
- Чому обрали Redis замість PostgreSQL LISTEN/NOTIFY?
- Запиши в маркер для майбутнього

### 5. **Не затягуй сесію**
- Максимум 3-4 файли за сесію
- Якщо токени закінчуються → закрий сесію

---

## 🔄 Приклад переходу між сесіями

### Сесія 1 (закінчення):
```markdown
# 🔖 SESSION END: AI Provider Fix

## ✅ Completed:
- [x] Changed Gemini model to gemini-1.5-flash
- [x] Tested /api/chat — no more 404 errors

## 📊 Current state:
- Server: running, no errors
- AI: Gemini responds correctly

## 🚀 Next session:
MODULE: Telegram Bot Polish
TASK: Add timeouts to prevent TimedOut errors
```

### Сесія 2 (початок):
```markdown
# 🔖 SESSION START: Telegram Bot Polish

## Previous session recap:
[Paste SESSION END from above]

## Goals for this session:
1. Add connect_timeout and read_timeout to Application.builder()
2. Test: no TimedOut errors after 5 minutes

---

[Claude continues work here]
```

---

## 📚 Додаткові ресурси

### Інструменти для tracking:
- GitHub Projects (створи Kanban board)
- Notion (для SESSION маркерів)
- Google Sheets (простий чеклист)

### Коли створювати нову сесію:
- ✅ Попередня досягла 150K+ токенів
- ✅ Завершено модуль (все працює)
- ✅ Зміна фокусу (AI → Telegram → API)
- ❌ НЕ в середині дебагу (закінчи спочатку)

---

**Версія:** 1.0.0  
**Останнє оновлення:** 2026-02-05  
**Автор:** Healer Nexus Team  
**Використання:** Копіюй SESSION маркери в кожну нову розмову з Claude
