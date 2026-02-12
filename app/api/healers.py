from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.connection import get_db
from app.models.healer import Healer
from typing import List

router = APIRouter()

@router.get("/")
async def get_healers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Healer))
    return result.scalars().all()
