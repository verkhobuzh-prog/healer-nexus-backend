# 🌟 Healer Nexus Platform

**Hybrid AI-Human marketplace** для цілителів, енергопрактиків, коучів, вчителів, 3D дизайнерів та майстрів з ремонту квартир.

## 🚀 Можливості (Autonomous v2.1)
- **Hybrid Delivery**: Вибір між AI-агентом (миттєво для дизайну/консультацій) та людиною-експертом.
- **Smart Niche Detection**: Автоматичне розпізнавання запиту (Wellness, Creative, Home Services).
- **Global Reach**: Підтримка регіонів (EU, Ukraine, US, Canada).
- **Multi-Agent System**: Вбудовані агенти для прогріву лідів та саморефлексії коду.

## 📦 Структура
- `app/ai/` — Інтелектуальне ядро (Gemini, prompts, reflection).
- `app/api/` — FastAPI ендпоінти (Chat, Specialists, Services).
- `app/models/` — SQLAlchemy моделі (Specialist, User, Message).
- `app/telegram/` — Гібридні боти для клієнтів та адмінів.

## 🛠 Запуск
1. `pip install -r requirements.txt`
2. `cp .env.example .env` (додайте свій GEMINI_API_KEY)
3. `export PYTHONPATH=$PYTHONPATH:.`
4. `uvicorn app.main:app --reload`
Last update: 2026-02-04
