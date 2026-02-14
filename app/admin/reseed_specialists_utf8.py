"""
Re-seed specialist names/specialties with UTF-8 from SPECIALISTS_SPEC.
Fixes "???????" display when DB had encoding issues. Updates existing rows by order.
Run: python -m app.admin.reseed_specialists_utf8
"""
from __future__ import annotations

import asyncio
import logging
from sqlalchemy import select

from app.database.connection import async_session_maker
from app.models.specialist import Specialist
from app.admin.pre_seed_learning import SPECIALISTS_SPEC

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def reseed_specialists_utf8() -> None:
    """Update first N specialists with UTF-8 name/specialty from SPECIALISTS_SPEC."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Specialist).order_by(Specialist.id).limit(len(SPECIALISTS_SPEC))
        )
        specialists = list(result.scalars().all())
        if not specialists:
            logger.warning("No specialists found. Run pre_seed_learning first.")
            return
        for i, spec_row in enumerate(SPECIALISTS_SPEC):
            if i >= len(specialists):
                break
            s = specialists[i]
            s.name = spec_row["name"]
            s.specialty = spec_row["specialty"]
            logger.info("Updated specialist id=%s: %s — %s", s.id, s.name, s.specialty)
        await session.commit()
    logger.info("Re-seeded %s specialists with UTF-8.", min(len(specialists), len(SPECIALISTS_SPEC)))


if __name__ == "__main__":
    asyncio.run(reseed_specialists_utf8())
