# Дослідження: чому не вдається увійти в акаунт спеціаліста

**Мета:** знайти причину, через яку спеціаліст (practitioner) не може увійти в систему, **без зміни коду** — лише перевірки та гіпотези.

---

## Контекст архітектури

1. **Ролі:** У системі є ролі `user`, `practitioner`, `admin`. Спеціаліст у сенсі «практик з блогом/записом» = користувач з роллю **`practitioner`**.

2. **Ланцюжок даних для входу практика:**
   - **User** (email, password_hash, **role**) — логін по email/паролю.
   - **Specialist** (user_id → users.id) — один рядок на користувача-практика.
   - **PractitionerProfile** (specialist_id → specialists.id, **project_id**) — профіль у конкретному проєкті (наприклад `healer_nexus`).

3. **Потік логіну (коротко):**
   - `POST /api/auth/login` → `AuthService.login(email, password)`.
   - Перевірка: User за email, перевірка пароля, is_active.
   - `_get_user_ids(user)` шукає Specialist по `user_id`, потім PractitionerProfile по `specialist_id` + `project_id`.
   - В JWT access token кладуться: `role`, `specialist_id`, `practitioner_id`.
   - Якщо `practitioner_id` в токені немає — виклики ендпоінтів з `get_current_practitioner` повертають **403 Not a practitioner**.

4. **Як користувач стає практиком:**
   - Подає заявку `POST /api/auth/apply-specialist` (будучи звичайним user).
   - Адмін в `PUT /api/admin/applications/{app_id}` з `status: "approved"` створює Specialist, PractitionerProfile і ставить **user.role = "practitioner"**.

---

## Що саме «не вдається увійти» — уточнити

Перед перевірками варто чітко фіксувати сценарій:

- **A)** При логіні (email + пароль) одразу **401** або повідомлення на кшталт «Invalid email or password» / «Account is inactive».
- **B)** Логін повертає **200** і токени, але потім при відкритті дашборду/блогу/аналітики — **403** (наприклад «Not a practitioner»).
- **C)** Помилка на етапі **refresh** токенів (наприклад після оновлення сторінки).
- **D)** Інше (наприклад редірект на логін, біла сторінка, помилка тільки на певних ендпоінтах).

Від цього залежить, куди дивитися в першу чергу (БД User vs Specialist/Profile vs JWT/фронт).

---

## Перевірки (без зміни коду)

### 1. Користувач у таблиці `users`

Для email спеціаліста виконати (або еквівалент у клієнті БД):

```sql
SELECT id, email, username, role, is_active,
       (password_hash IS NOT NULL AND length(password_hash) > 0) AS has_password
FROM users
WHERE email = 'EMAIL_СПЕЦІАЛІСТА';
```

Перевірити:

- **role** = `'practitioner'`. Якщо `user` — після approve заявки роль могла не оновитися або оновлення не закомітилось.
- **is_active** = true. Якщо false — логін правильно дасть «Account is inactive».
- **has_password** = true. Якщо false — логін по паролю неможливий (наприклад користувач створений тільки через Telegram).

---

### 2. Запис Specialist для цього користувача

```sql
SELECT s.id AS specialist_id, s.user_id, s.name
FROM specialists s
JOIN users u ON u.id = s.user_id
WHERE u.email = 'EMAIL_СПЕЦІАЛІСТА';
```

Очікується один рядок. Якщо рядків немає — у JWT не буде `specialist_id`, і залежності типу `get_current_specialist` дадуть 403. Причина може бути: заявку не апрувили, апрув не створив Specialist, або створено з іншим user_id.

---

### 3. Запис PractitionerProfile для цього спеціаліста та проєкту

Значення `project_id` у коді береться з `settings.PROJECT_ID` (наприклад `healer_nexus`). Перевірка:

```sql
SELECT pp.id AS practitioner_id, pp.specialist_id, pp.project_id, pp.slug
FROM practitioner_profiles pp
JOIN specialists s ON s.id = pp.specialist_id
JOIN users u ON u.id = s.user_id
WHERE u.email = 'EMAIL_СПЕЦІАЛІСТА'
  AND pp.project_id = 'healer_nexus';
```

(Якщо в проді інший `PROJECT_ID` — підставити його.)

Очікується один рядок. Якщо рядків немає — `_get_user_ids` поверне `practitioner_id = None`, в JWT не потрапить `practitioner_id`, і всі ендпоінти з `get_current_practitioner` повернуть **403 Not a practitioner** навіть при успішному логіні.

---

### 4. Що реально повертає логін

Викликати логін з відомими email/паролем і перевірити тіло відповіді (наприклад у браузері / Postman):

```http
POST /api/auth/login
Content-Type: application/json

{"email": "EMAIL", "password": "PASSWORD"}
```

У відповіді перевірити:

- **status:** 200 чи 401.
- **user.role** — має бути `practitioner`.
- **user.specialist_id** — має бути число (id з таблиці specialists).
- **user.practitioner_id** — має бути число (id з practitioner_profiles). Якщо **null** — причина 403 після логіну: профіль не знайдено або інший project_id.

Якщо логін повертає 401 — дивитися на крок 1 (пароль, is_active, наявність password_hash).

---

### 5. Вміст JWT access token

Після успішного логіну взяти `access_token` з відповіді і розшифрувати (наприклад на [jwt.io](https://jwt.io) або локальним скриптом з тим самим `JWT_SECRET_KEY`). У payload перевірити:

- **sub** — user id.
- **role** — `practitioner`.
- **specialist_id** — присутній і збігається з БД.
- **practitioner_id** — присутній і збігається з БД. Якщо поля немає — причина 403: при створенні токена `_get_user_ids` повернув None для practitioner_id.

---

### 6. Консистентність після approve заявки

Якщо спеціаліст з’явився через заявку (apply-specialist → admin approve), перевірити:

- У таблиці **specialist_applications** для цього user_id є запис з **status** = `approved`.
- В одній транзакції при approve створюються: один Specialist (user_id = application.user_id), один PractitionerProfile (specialist_id = новий specialist.id, project_id = "healer_nexus") і оновлюється user.role = "practitioner". Можливі помилки: exception після створення Specialist і до commit (тоді Profile не створений), або помилка при оновленні user.role.

Перевірки з кроків 1–3 як раз показують результат цієї транзакції.

---

### 7. Пароль і способи створення користувача

- Якщо користувач створювався **тільки через Telegram** (без реєстрації по email), у нього може не бути **password_hash**. Тоді логін по email/паролю завжди дасть «Invalid email or password» — це очікувана поведінка, а не баг логіку.
- Якщо пароль скидав адмін через `PUT /api/admin/users/{user_id}/password` — переконатися, що в БД зберігається саме **password_hash** (не інше поле) і що після скидання логін тестовими даними працює.

---

## Гіпотези (коротко)

| Симптом | Ймовірна причина | Що перевірити |
|--------|------------------|----------------|
| 401 при логіні | Невірний пароль, немає password_hash, is_active=false | Крок 1, 7 |
| 200 при логіні, далі 403 на дашборді/блозі | В JWT немає practitioner_id | Кроки 2, 3, 4, 5 |
| 403 «Not a practitioner» | Немає PractitionerProfile або project_id не збігається | Крок 3, PROJECT_ID у налаштуваннях |
| Після approve «не може увійти» | role не оновлено або не створено Specialist/Profile | Кроки 1, 2, 3, 6 |

---

## Промпт для подальшого розслідування (скопіюй у Cursor/чат)

Можна використати такий текст, підставивши факти:

```
Проблема: спеціаліст (practitioner) не може увійти в акаунт.

Результати перевірок (заповни після виконання):
- Логін повертає: [ 200 / 401 ] — тіло user з відповіді: role=..., specialist_id=..., practitioner_id=...
- У БД для email ... : users.role=..., users.is_active=..., has password_hash=...
- У БД є Specialist з user_id=... : так / ні
- У БД є PractitionerProfile для цього specialist та project_id=... : так / ні
- У JWT access_token є specialist_id та practitioner_id: так / ні

Сценарій: [ A — 401 при логіні / B — 200 далі 403 / C — помилка при refresh / D — інше ]

Потрібно: на основі цього контексту та коду в app/services/auth_service.py, app/api/auth_router.py, app/api/deps.py знайти причину і запропонувати виправлення (з мінімальними змінами коду). Код поки не змінювати — лише висловити висновок і план фіксу.
```

Після заповнення результатів перевірок і сценарію можна передати цей блок у наступний діалог — тоді можна буде точно вказати місце поломки і запропонувати конкретні зміни в коді.
