# CURSOR SESSION: AI Agents Integration
# Project: Healer Nexus
# Date: 13 March 2026
# Task: Integrate AI Agent system into existing FastAPI project

## CONTEXT
Healer Nexus is a FastAPI app with PostgreSQL (Cloud SQL), JWT auth, Gemini AI.
We're adding an AI Agent system: 5 background agents that monitor health, security,
bugs, run QA tests, and provide AI recommendations.

## FILES TO CREATE (copy from agents_package/)

### 1. app/agents/__init__.py
### 2. app/agents/base_agent.py
### 3. app/agents/health_check_agent.py
### 4. app/agents/security_agent.py
### 5. app/agents/bug_scanner_agent.py
### 6. app/agents/qa_tester_agent.py
### 7. app/agents/advisor_agent.py
### 8. app/agents/agent_manager.py
### 9. app/models/agent_config.py
### 10. app/api/agent_router.py

## FILES TO MODIFY

### app/main.py
Add import at top with other routers:
```python
from app.api.agent_router import router as agent_router
```

Add router registration with other include_router calls:
```python
app.include_router(agent_router)
```

In startup() function, add BEFORE "Healer Nexus started" log:
```python
    # AI Agents
    from app.agents.agent_manager import agent_manager
    await agent_manager.start_all()
```

In shutdown() function, add:
```python
    # Stop AI Agents
    from app.agents.agent_manager import agent_manager
    await agent_manager.stop_all()
```

### app/database/connection.py
Add model imports (where other models are imported):
```python
from app.models.agent_config import AgentConfig, AgentLog
```

Ensure async_session_factory is exported. If not present, add after engine creation:
```python
from sqlalchemy.ext.asyncio import async_sessionmaker
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
```

### app/config.py
Add to Settings class:
```python
    TELEGRAM_ADMIN_CHAT_ID: str | None = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
```

### requirements.txt
Add if not present:
```
httpx>=0.25.0
```

## VERIFICATION
```bash
python -c "from app.agents.agent_manager import agent_manager; print('OK')"
uvicorn app.main:app --reload
# Check logs for "Agent Manager: starting all agents..."
```

## IMPORTANT NOTES
- All agents start in DISABLED state (safe by default)
- Admin must explicitly enable agents via API
- Agents use existing get_current_admin from deps.py
- Tables agent_configs and agent_logs are created via create_all()
- No Alembic migration needed if using create_all() on startup
