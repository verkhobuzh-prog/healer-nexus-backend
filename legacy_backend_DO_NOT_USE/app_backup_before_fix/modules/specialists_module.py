from typing import Dict, Any
from datetime import datetime
from sqlalchemy import select, func
from app.core.base_module import BaseModule
from app.database.connection import async_session_maker
from app.models.specialist import Specialist

class SpecialistsModule(BaseModule):
    def __init__(self): super().__init__("specialists")
    
    async def health_check(self) -> Dict[str, Any]:
        async with async_session_maker() as db:
            res = await db.execute(select(func.count(Specialist.id)))
            total = res.scalar()
            return {
                "status": "healthy" if total > 0 else "degraded",
                "total_specialists": total,
                "timestamp": datetime.now().isoformat()
            }
