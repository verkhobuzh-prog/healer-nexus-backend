from fastapi import APIRouter
from app.models.specialist import Specialist
# Тут пізніше додамо логіку отримання списку з БД

router = APIRouter()

@router.get("/specialists")
async def get_specialists():
    return {"message": "Список спеціалістів буде тут"}
