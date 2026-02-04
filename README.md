<<<<<<< HEAD
﻿# Healer Nexus Platform
AI-Powered Multi-Project Orchestration Platform
## Quick Start
```bash
# 1. Clone
git clone <repo-url>
cd healer-backend
# 2. Setup env
cd backend
cp ../.env.example .env
# Edit .env with real keys
# 3. Install
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
# 4. Migrate
set PYTHONPATH=.
alembic upgrade head
# 5. Run
uvicorn app.main:app --reload
```
## Features
- FastAPI + SQLAlchemy 2.0 async
- Telegram bot with AI chat
- Gemini AI integration
- Health monitoring + metrics
- Multi-project support
## Tech Stack
Python 3.13 • FastAPI • SQLite/PostgreSQL • Gemini AI • python-telegram-bot
=======
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
>>>>>>> c6b71ffb1c84f2e6046d2bad0b45e5cbce483b1c
