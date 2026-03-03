# Інструкція: реєстрація адміна, внесення та редагування спеціалістів

Документ описує порядок дій на платформі Healer Nexus **без змін у коді** — лише використання API та/або бази даних.

---

## 1. Порядок реєстрації адміна на платформі

Через публічний API **неможливо** зареєструвати користувача з роллю `admin`: при реєстрації допускаються лише ролі `user`, `practitioner`, `specialist`.

### Варіант А: Перший адмін (коли адмінів ще немає)

1. **Зареєструйте звичайного користувача** через API:
   - **POST** `/api/auth/register`
   - Тіло (JSON): `email`, `password`, `name`, `role: "user"` (або `practitioner` / `specialist` за потреби).

2. **Призначте йому роль адміна одним із способів:**
   - **Через базу даних:** оновіть запис у таблиці `users` для цього користувача: `role = 'admin'`.
   - **Через API (якщо вже є хтось з доступом до БД):** після встановлення `role = 'admin'` у БД цей користувач зможе входити як адмін і далі призначати інших адмінів через API (див. варіант Б).

### Варіант Б: Додатковий адмін (коли вже є хоча б один адмін)

1. Новий користувач **реєструється** як звичайний користувач:
   - **POST** `/api/auth/register` з `role: "user"` (або `practitioner` / `specialist`).

2. Існуючий адмін **авторизується** і змінює роль:
   - **POST** `/api/auth/login` — отримати `access_token`.
   - **PUT** `/api/admin/users/{user_id}/role`  
     Заголовок: `Authorization: Bearer <access_token>`.  
     Тіло: `{"role": "admin"}`.

Після цього користувач з `user_id` отримує роль `admin` і може користуватися адмін-ендпоінтами.

---

## 2. Порядок внесення спеціалістів

Є **два** способи появи спеціаліста на платформі.

### Спосіб 1: Пряме створення через API (адмін або спеціаліст)

1. Увійти в систему (отримати JWT):
   - **POST** `/api/auth/login` (email, password) → `access_token`.

2. Створити спеціаліста:
   - **POST** `/api/specialists`  
     Заголовок: `Authorization: Bearer <access_token>`.  
     Роль користувача: `admin` або `specialist`.

   Обов’язкові поля в тілі (JSON):
   - `name` — ім’я
   - `service_type` — тип послуги (наприклад `healer`, `coach`, `teacher_math`, `interior_designer`)
   - `specialty` — спеціалізація
   - `hourly_rate` — ставка (число, можна 0)
   - `delivery_method` — за замовчуванням `"human"` (можна `ai_assisted`, `fully_ai`)

   Опційно: `bio`, `telegram_id`, `portfolio_url`, `latitude`, `longitude`, `is_ai_powered`, `ai_model`, `ai_capabilities`.

3. У відповіді повертається створений спеціаліст (з `id`). Він одразу активний і може бути використаний у пошуку/бронюванні (якщо є профіль практика для проекту — за потреби його можна додати окремо).

### Спосіб 2: Заявка користувача → розгляд адміном

1. Користувач (з роллю `user`) **подає заявку** на спеціаліста:
   - **POST** `/api/auth/apply-specialist`  
     Заголовок: `Authorization: Bearer <access_token>` (токен цього користувача).

   Тіло (JSON): `name`, `specialty`, `service_type`, `bio`, опційно `experience_years`, `motivation`, `hourly_rate`, `contact_telegram`.

2. Заявка потрапляє в список зі статусом `pending`.

3. Адмін **переглядає заявки**:
   - **GET** `/api/admin/applications`  
     Заголовок: `Authorization: Bearer <access_token>` (адмін).  
     Опційно: `?status=pending` (або `approved`, `rejected`).

4. Адмін **приймає або відхиляє** заявку:
   - **PUT** `/api/admin/applications/{app_id}`  
     Тіло: `{"status": "approved"}` або `{"status": "rejected"}`, опційно `"admin_comment"`.

   При **approved**:
   - створюється запис у таблиці `specialists` (з `user_id` заявника);
   - створюється профіль у `practitioner_profiles` (проект `healer_nexus`);
   - роль користувача змінюється на `practitioner`.

Підсумок: спеціаліст може з’явитися або **напряму** (POST `/api/specialists` від адміна/спеціаліста), або **через заявку** (apply-specialist → адмін approve).

---

## 3. Порядок редагування спеціалістів

1. **Авторизація:** користувач з роллю `admin` або `specialist` отримує токен:
   - **POST** `/api/auth/login`.

2. **Отримання поточних даних (за потреби):**
   - **GET** `/api/specialists/{specialist_id}` — один спеціаліст;
   - або **GET** `/api/specialists` — список (опційно `?service_type=...`).

3. **Оновлення спеціаліста:**
   - **PUT** `/api/specialists/{specialist_id}`  
     Заголовок: `Authorization: Bearer <access_token>`.  
     Роль: `admin` або `specialist`.

   Тіло (JSON) — усі поля опційні, передаються лише ті, що змінюються:
   - `name`
   - `specialty`
   - `service_types` (список рядків)
   - `hourly_rate` (має бути > 0, якщо передається)
   - `bio`
   - `delivery_method` (`human` | `ai_assisted` | `fully_ai`)

4. У відповіді повертається оновлений спеціаліст.

**М’яке видалення (деактивація):**  
- **DELETE** `/api/specialists/{specialist_id}` (з токеном адміна або спеціаліста) — встановлює `is_active = False`; спеціаліст перестає відображатися в публічних списках/пошуку.

---

## Коротка довідка ендпоінтів

| Дія | Метод | URL | Хто |
|-----|--------|-----|-----|
| Реєстрація | POST | `/api/auth/register` | Публічно (ролі: user, practitioner, specialist) |
| Вхід | POST | `/api/auth/login` | Публічно |
| Зміна ролі на admin | PUT | `/api/admin/users/{user_id}/role` | Адмін |
| Список заявок на спеціаліста | GET | `/api/admin/applications` | Адмін |
| Прийняти/відхилити заявку | PUT | `/api/admin/applications/{app_id}` | Адмін |
| Заявка на спеціаліста | POST | `/api/auth/apply-specialist` | Авторизований user |
| Створити спеціаліста | POST | `/api/specialists` | Адмін або specialist |
| Список спеціалістів | GET | `/api/specialists` | Публічно |
| Один спеціаліст | GET | `/api/specialists/{id}` | Публічно |
| Редагувати спеціаліста | PUT | `/api/specialists/{id}` | Адмін або specialist |
| Деактивувати спеціаліста | DELETE | `/api/specialists/{id}` | Адмін або specialist |

У всіх захищених ендпоінтах у заголовку вказується: `Authorization: Bearer <access_token>`.
