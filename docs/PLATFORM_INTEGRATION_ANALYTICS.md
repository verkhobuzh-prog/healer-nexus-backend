# Аналітика платформи Healer Nexus: стек інтеграції, сигнали, відновлення, блоки

**Мета:** зрозуміти, що вже є з інтеграції між блоками, сигнальних системах, алгоритмах відновлення та модульній структурі. Код не змінювався.

---

## 1. Чіткий стек інтеграції між блоками

### Що є (готове)

| Шар | Що реалізовано | Де подивитися |
|-----|-----------------|----------------|
| **Точка входу** | Один FastAPI-додаток, усі роутери підключені в `main.py` з єдиними префіксами (`/api`, `/api/dashboard`, тощо). | `app/main.py` (include_router) |
| **Доступ до БД** | Єдина точка: `get_db()` → `async_session_maker`. Усі API та сервіси отримують сесію через `Depends(get_db)`. | `app/database/connection.py`, `app/api/deps.py` |
| **Авторизація** | Єдиний набір залежностей: `get_current_user`, `get_current_practitioner`, `get_current_specialist`, `get_current_admin`, `require_role()`. Роутери явно оголошують, хто має доступ. | `app/api/deps.py`, використання в усіх `*_router.py` |
| **Конфіг** | Один об’єкт `settings` (Pydantic BaseSettings) з `.env`. Ключі, URL, feature toggles (GEMINI_ENABLED тощо) — з одного місця. | `app/config.py` |
| **Мультипроєкт** | Єдиний ідентифікатор `PROJECT_ID` (наприклад `healer_nexus`). Сервіси приймають `project_id` і фільтрують дані. Реєстр проєктів: `ModuleRegistry` (child projects для адміна). | `app/config.py`, `app/core/module_registry.py`, виклики типу `BlogService(session, project_id)` |

### Як це виглядає на практиці

- **Блок A (Chat)** викликає **Блок B (Specialists/Booking)** тільки через **сервіси**: `ChatToolExecutor` → `SpecialistMatcher`, `BookingService`, `RecommendationService`. Прямих викликів між роутерами немає.
- **Блок Blog** після публікації поста викликає **нотифікатор** `notify_post_published` → `blog_telegram_service`. Це єдиний явний “сигнал” між блогом і зовнішнім каналом (Telegram).
- **Інтеграція між блоками** йде через:
  - спільну **сесію БД** (передається в сервіси);
  - **прямі імпорти сервісів** (немає шини подій або черг — див. нижче).

### Чого немає (зазвичай очікується в “чіткому стеку”)

- **Немає єдиного документованого контракту API** (наприклад OpenAPI-схеми для внутрішніх сервісів) — контракт неявний (сигнатури функцій).
- **Немає абстракції “блок = окремий сервіс/контейнер”** — все в одному процесі, блоки = модулі Python (api/*, services/*).
- **Немає черг/повідомлень** (Redis, Pub/Sub тощо) — все синхронні виклики в межах одного запиту або фонової задачі.

---

## 2. Сигнальні системи кооперації / інтеграції

### Що є (готове)

| Сигнал / механізм | Призначення | Де реалізовано |
|-------------------|-------------|-----------------|
| **Виклик після публікації поста** | Після `publish_post` / `publish_scheduled_posts` викликається `notify_post_published(session, post)` → Telegram-канал. | `blog_service.py` → `blog_publish_notifier.py` → `blog_telegram_service.py` |
| **Повідомлення спеціалісту про букінг** | Після створення букінгу викликається `notify_specialist_telegram(booking)`. | `booking_service.py` (create_booking → notify_specialist_telegram) |
| **Function calling у чаті** | Gemini викликає інструменти `search_specialists`, `create_booking`, `get_specialist_details`; `ChatToolExecutor` виконує їх і повертає результат назад в AI. | `ai/providers.py` (tools), `services/chat_tool_executor.py` |
| **Feature flags** | По `project_id` можна вмикати/вимикати поведінку (personalized_bots, emotion_analysis, ethical_disclaimer). Використовується в AI/чаті. | `app/core/feature_flags.py` |
| **GEMINI_ENABLED** | Глобальний вимикач AI: чат повертає 503, scheduler не стартує. | `config.py`, `main.py` startup, `api/chat.py` |

### Що згадано в коді, але не реалізовано

| Елемент | Де згадано | Стан |
|---------|------------|------|
| **EventBus** | `brain_core.py`: імпорт `app.core.event_bus.get_event_bus`, emit `bot.update_strategy`. `feature_flags.py`, `emotion_analysis.py`: коментарі про EventBus. | Модуля `app/core/event_bus.py` **немає**. Виклик обгорнутий у try/except, помилка ігнорується (“норма для stub”). |
| **Сигнали зміни feature flags** | Коментар: “EventBus can emit flag changes”. | Немає реалізації. |

### Як побачити поточні “сигнали”

- **Блог → Telegram:** логіка в `blog_publish_notifier.notify_post_published` і `blog_telegram_service.send_post_announcement`.
- **Букінг → Telegram:** `booking_service.notify_specialist_telegram`.
- **Чат → пошук/букінг:** `chat_tool_executor.execute_tool_call` за іменами функцій від Gemini.
- **Feature flags:** `feature_flags.get_flag(project_id, flag_name)`.

---

## 3. Алгоритми відновлення

### Що є (готове)

| Сценарій | Що зроблено | Де |
|----------|-------------|-----|
| **Чат: помилка AI** | При будь-якому exception повертається fallback-відповідь з `SafeModeContext` (OUTAGE, RATE_LIMIT, TIMEOUT, ERROR). Користувач отримує текст, а не 500. | `api/chat.py` (except → get_fallback_response), `resilience/safe_mode.py` |
| **БД: помилка create_all (SQLite)** | При помилці init_db для SQLite — видалення файлу БД і повторне створення таблиць. Для не-SQLite — лише лог і продовження. | `database/connection.py` (init_db) |
| **БД: pool** | `pool_pre_ping=True` — перевірка з’єднання перед використанням. | `database/connection.py` (create_async_engine) |
| **Scheduler / Aggregator** | У циклі: при exception логирується помилка, цикл продовжується (sleep і далі). Один збій не зупиняє фонову задачу. | `blog_scheduler.py`, `blog_analytics_aggregator.py` |
| **Публікація поста → нотифікація** | Виклик `notify_post_published` обгорнутий у try/except; помилка не пробрасывается — публікація вважається успішною навіть якщо Telegram не відправив. | `blog_service.py` (publish_post, publish_scheduled_posts) |
| **Букінг → Telegram** | `notify_specialist_telegram` у try/except; при помилці логирується, букінг все одно створюється. | `booking_service.py` (create_booking) |
| **Рекомендації в чаті** | `record_recommendation` / `record_details_viewed` у try/except — помилка ігнорується, основний результат (пошук/деталі) повертається. | `chat_tool_executor.py` |

### Чого немає

- **Повторні спроби (retry/backoff)** для зовнішніх викликів (Gemini, Telegram, Cloudinary) — немає уніфікованого шару.
- **Таймаути** на виклики Gemini (ризик “висить довго”).
- **Circuit breaker** — немає.
- **Єдиний глобальний exception handler** у FastAPI для логування та уніфікованої відповіді 5xx.

---

## 4. Система створення “блокового” коду (модульність, розширюваність)

### Що є (готове)

| Механізм | Опис | Де подивитися |
|----------|------|-------------------------------|
| **Роутери як блоки** | Новий “блок” = новий APIRouter, підключення в `main.py` через `app.include_router(router, prefix=...)`. Чітко видно список усіх HTTP-блоків. | `main.py` (блок роутерів) |
| **Сервіси як шари** | Бізнес-логіка в `services/*`. Роутери тонкі: перетворення запит/відповідь + виклик сервісу. Додати новий “блок” = новий сервіс + опційно роутер. | Будь-який `api/*_router.py` (виклик сервісів) |
| **Залежності FastAPI** | `get_db`, `get_current_user`, `get_current_practitioner` тощо — повторно використовуються в багатьох роутерах. Додати новий роутер з тими ж правилами доступу просто. | `api/deps.py` |
| **ModuleRegistry** | Реєстрація “дочірніх” project_id для мультипроєкту. Розширення списку проєктів без зміни логіки сервісів. | `core/module_registry.py` |
| **ServiceRegistry** | Каталог типів послуг (wellness, coaching, creative, home) — список ServiceDefinition. Додати новий тип послуги = додати запис у список. | `core/service_registry.py` |
| **Feature flags** | Увімкнення/вимкнення поведінки по project_id. Новий прапорець можна додати в `_DEFAULT_FLAGS` і використовувати в коді. | `core/feature_flags.py` |

### Як додати новий “блок” (без зміни існуючого коду в логіці)

1. **Новий HTTP-блок:** створити `app/api/new_router.py`, визначити роутер, в `main.py` додати `app.include_router(new_router, prefix="/api/...")`.
2. **Нова фонова задача:** клас з `start()`/`stop()` та циклом (за аналогією з `BlogScheduler`), у `main.py` в startup викликати `await new_task.start()`, в shutdown — `await new_task.stop()`.
3. **Новий тип послуги:** додати `ServiceDefinition` у `SERVICES` у `service_registry.py`.
4. **Новий проєкт:** викликати `get_registry().register_child_project(project_id)` (або додати в конфіг/БД при ініціалізації).

### Чого немає

- **Плагінів** — немає динамічного завантаження модулів з конфігу.
- **EventBus** — немає єдиної шини подій для зв’язку між блоками без прямого імпорту.
- **Документованого “контракту” блоку** (наприклад, інтерфейс сервісу або подія) — все неявно.

---

## 5. Зведена таблиця: що готове, з чим можна працювати, як побачити

| Категорія | Що готове / є | З чим можна працювати | Як побачити |
|-----------|----------------|------------------------|-------------|
| **Стек інтеграції** | Один FastAPI, один get_db, один конфіг, єдиний PROJECT_ID, роутери та сервіси з явними залежностями. | Додавати нові роутери/сервіси за тим самим шаблоном; тримати контракт через сигнатури та project_id. | `main.py`, `database/connection.py`, `config.py`, будь-який `*_router.py` |
| **Сигнали кооперації** | Нотифікація після публікації поста (Telegram), нотифікація після букінгу (Telegram), function calling чат→пошук/букінг, feature flags, GEMINI_ENABLED. | Додавати нові виклики після подій (аналог `notify_post_published`); розширювати tools у Gemini; додавати прапорці в feature_flags. | `blog_publish_notifier.py`, `booking_service.py`, `chat_tool_executor.py`, `feature_flags.py`, `api/chat.py` |
| **Відновлення** | Safe mode у чаті, pool_pre_ping БД, відновлення SQLite при помилці create_all, “не падати” у scheduler/aggregator та при нотифікаціях (try/except). | Додати retry/backoff та таймаути для Gemini/Telegram; опційно — глобальний exception handler у FastAPI. | `resilience/safe_mode.py`, `api/chat.py`, `database/connection.py`, `blog_scheduler.py`, `blog_analytics_aggregator.py`, `blog_service.py`, `booking_service.py` |
| **Блокова/модульна структура** | Роутери як блоки, сервіси як шар логіки, Depends для авторизації та БД, ModuleRegistry, ServiceRegistry, feature flags. | Додавати нові роутери, сервіси, типи послуг, проєкти та прапорці без переписування ядра. | `main.py`, `api/deps.py`, `core/module_registry.py`, `core/service_registry.py`, `core/feature_flags.py` |
| **EventBus** | Згаданий у коментарях і в brain_core (emit стратегій для ботів). | Модуль `event_bus` відсутній — можна реалізувати і підключити в brain_core та feature_flags. | Пошук по "event_bus", "get_event_bus", "EventBus" у проєкті |
| **Моніторинг** | `automation/monitoring.py` збирає CPU/RAM/disk, порівнює з `settings.CRITICAL_CPU` / `CRITICAL_RAM`. | У `config.py` немає полів CRITICAL_CPU/CRITICAL_RAM — або додати в Settings, або прибрати з monitoring. | `automation/monitoring.py`, `config.py` |

---

## 6. Висновки

- **Чіткий стек інтеграції:** є в межах одного застосунку: один вхід (FastAPI), одна БД-сесія, один конфіг, явні залежності та project_id. Чіткої міжсервісної шини або контрактів на рівні подій/API немає.
- **Сигнальні системи:** є кілька точок “після події X викликати Y” (блог→Telegram, букінг→Telegram, чат→tools). EventBus лише згаданий, не реалізований.
- **Алгоритми відновлення:** є м’яке падіння (fallback у чаті, продовження роботи scheduler/aggregator, ігнорування помилок нотифікацій). Немає retry, таймаутів, circuit breaker, єдиного глобального обробника помилок.
- **Блоковий код:** додавати нові роутери, сервіси, типи послуг і проєкти зручно; є реєстри та feature flags. Немає плагінів та реальної шини подій.

Документ можна використовувати як орієнтир, що вже готове і з чим можна працювати, без змін коду.
