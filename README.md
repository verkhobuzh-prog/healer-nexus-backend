# Healer Nexus Platform
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
