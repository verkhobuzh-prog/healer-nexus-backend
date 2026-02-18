"""
Shared FastAPI dependencies (auth, db).
"""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.practitioner_profile import PractitionerProfile
from app.config import settings


async def get_current_practitioner(
    x_practitioner_id: Optional[str] = Header(None, alias="X-Practitioner-Id"),
    db: AsyncSession = Depends(get_db),
) -> PractitionerProfile:
    """
    Resolve practitioner from X-Practitioner-Id header (for blog ownership).
    In production, replace with JWT or API key auth.
    """
    if not x_practitioner_id or not x_practitioner_id.strip():
        raise HTTPException(
            status_code=401,
            detail="Missing X-Practitioner-Id header",
        )
    try:
        pid = int(x_practitioner_id.strip())
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid X-Practitioner-Id")
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    r = await db.execute(
        select(PractitionerProfile).where(
            PractitionerProfile.id == pid,
            PractitionerProfile.project_id == project_id,
            PractitionerProfile.is_active == True,
        )
    )
    practitioner = r.scalar_one_or_none()
    if not practitioner:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    return practitioner
