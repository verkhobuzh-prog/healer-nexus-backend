"""
Agent Router — API для управління AI-агентами.
Всі endpoints доступні тільки admin.

Endpoints:
  GET    /api/agents/status          — статус усіх агентів
  GET    /api/agents/logs            — логи агентів (з фільтрами)
  POST   /api/agents/{name}/enable   — увімкнути агента
  POST   /api/agents/{name}/disable  — вимкнути агента
  POST   /api/agents/{name}/run      — ручний запуск
  PUT    /api/agents/{name}/config   — оновити конфігурацію
  GET    /api/agents/{name}/logs     — логи конкретного агента
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.api.deps import get_current_admin
from app.agents.agent_manager import agent_manager

router = APIRouter(prefix="/api/agents", tags=["agents"])


# ─── Schemas ──────────────────────────────────────────

class AgentConfigUpdate(BaseModel):
    interval_seconds: int | None = None
    notify_telegram: bool | None = None
    notify_on_severity: str | None = None  # info | warning | error | critical
    config: dict | None = None


# ─── Endpoints ────────────────────────────────────────

@router.get("/status")
async def agents_status(admin=Depends(get_current_admin)):
    """Статус усіх AI-агентів."""
    return await agent_manager.get_status()


@router.get("/logs")
async def agents_logs(
    agent_name: str | None = Query(None, description="Filter by agent name"),
    severity: str | None = Query(None, description="Filter by severity"),
    limit: int = Query(50, ge=1, le=200),
    admin=Depends(get_current_admin),
):
    """Логи агентів з фільтрами."""
    return await agent_manager.get_logs(
        agent_name=agent_name,
        severity=severity,
        limit=limit,
    )


@router.post("/{agent_name}/enable")
async def enable_agent(agent_name: str, admin=Depends(get_current_admin)):
    """Увімкнути агента."""
    result = await agent_manager.enable_agent(agent_name)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/{agent_name}/disable")
async def disable_agent(agent_name: str, admin=Depends(get_current_admin)):
    """Вимкнути агента."""
    result = await agent_manager.disable_agent(agent_name)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/{agent_name}/run")
async def run_agent(agent_name: str, admin=Depends(get_current_admin)):
    """Ручний одноразовий запуск агента."""
    result = await agent_manager.run_agent_once(agent_name)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.put("/{agent_name}/config")
async def update_agent_config(
    agent_name: str,
    body: AgentConfigUpdate,
    admin=Depends(get_current_admin),
):
    """Оновити конфігурацію агента."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = await agent_manager.update_config(agent_name, updates)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{agent_name}/logs")
async def agent_logs(
    agent_name: str,
    severity: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    admin=Depends(get_current_admin),
):
    """Логи конкретного агента."""
    return await agent_manager.get_logs(
        agent_name=agent_name,
        severity=severity,
        limit=limit,
    )
