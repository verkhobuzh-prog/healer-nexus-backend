import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator

logger = logging.getLogger(__name__)

from app.api.deps import require_role, get_optional_user
from app.database.connection import get_db
from app.models.specialist import Specialist
from app.models.user import User
from app.services.recommendation_service import RecommendationService
from app.models.practitioner_profile import PractitionerProfile
from app.schemas.booking import SpecialistSearchResult, SpecialistMatchItem
from app.services.specialist_matcher import SpecialistMatcher
from app.config import settings

router = APIRouter(tags=["Specialists"])


def _project_id() -> str:
    return getattr(settings, "PROJECT_ID", "healer_nexus")

class SpecialistBase(BaseModel):
    """Базова схема — поля з default/Optional щоб не падати на даних з seed/БД."""
    name: str = Field(..., min_length=1, max_length=255)
    service_type: str = Field(..., description="healer | coach | 3d_modeling etc.")
    delivery_method: str = Field(default="human", description="human | ai_assisted | fully_ai")
    specialty: str = Field(..., max_length=200)
    hourly_rate: int = Field(0, ge=0, description="0 якщо не задано")
    bio: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

class SpecialistCreate(SpecialistBase):
    """
    Схема створення - ✅ ПОВНІСТЮ БЕЗ niche
    ✅ FIX #1: telegram_id тепер None за замовчуванням (не 0), щоб уникнути UNIQUE constraint
    """
    telegram_id: Optional[int] = Field(
        None,
        ge=1,
        examples=[123456789, None],
        description="Підтримує великі ID (BigInteger). Must be positive or null."
    )
    portfolio_url: Optional[str] = None
    is_ai_powered: bool = Field(default=False)
    ai_model: Optional[str] = None
    ai_capabilities: Optional[Dict[str, Any]] = None

class SpecialistResponse(SpecialistBase):
    """Схема відповіді — усі поля з default щоб серіалізація з ORM не падала."""
    id: int
    service_type: str
    service_types: Optional[List[str]] = None
    is_verified: bool = False
    is_active: bool = True
    telegram_id: Optional[int] = None
    portfolio_url: Optional[str] = None
    is_ai_powered: bool = False
    ai_model: Optional[str] = None
    ai_capabilities: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("hourly_rate", mode="before")
    @classmethod
    def coerce_hourly_rate(cls, v: Any) -> Any:
        """БД (наприклад SQLite/Postgres) може повертати float для INTEGER."""
        if v is None:
            return 0
        if isinstance(v, float) and not isinstance(v, bool):
            return int(v)
        return v

    @field_validator("service_types", mode="before")
    @classmethod
    def coerce_service_types(cls, v: Any) -> Any:
        """JSON колонка може повертатися як str з деяких драйверів."""
        if v is None:
            return None
        if isinstance(v, str):
            import json
            try:
                parsed = json.loads(v)
                return [str(x) for x in parsed] if isinstance(parsed, list) else [v]
            except Exception:
                return [v]
        if isinstance(v, list):
            return [str(x) for x in v]
        return None


class SpecialistUpdate(BaseModel):
    """Схема оновлення — усі поля опційні; hourly_rate > 0 якщо передано."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    service_types: Optional[List[str]] = None
    hourly_rate: Optional[int] = Field(None, gt=0)
    bio: Optional[str] = None
    specialty: Optional[str] = Field(None, max_length=200)
    delivery_method: Optional[str] = Field(None, description="human | ai_assisted | fully_ai")

    model_config = ConfigDict(from_attributes=True)

# --- Ендпоінти ---

@router.post("/specialists", response_model=SpecialistResponse, status_code=201)
async def create_specialist(
    data: SpecialistCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_role("admin", "specialist")),
):
    """Створення нового спеціаліста (admin або specialist)."""
    # .model_dump() замість .dict() для Pydantic v2
    new_specialist = Specialist(**data.model_dump())
    
    db.add(new_specialist)
    await db.commit()
    await db.refresh(new_specialist)
    return new_specialist

@router.get("/specialists", response_model=List[SpecialistResponse])
async def get_specialists(
    service_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Отримання списку з фільтром по service_type"""
    try:
        query = select(Specialist).where(Specialist.is_active == True)
        if service_type:
            query = query.where(Specialist.service_type == service_type)

        result = await db.execute(query)
        specialists = result.scalars().all()

        for s in specialists:
            logger.info(
                "Specialist id=%s name=%s service_type=%s service_types=%s delivery_method=%s hourly_rate=%s (type=%s)",
                s.id, s.name, getattr(s, "service_type", "N/A"), getattr(s, "service_types", "N/A"),
                getattr(s, "delivery_method", "N/A"), getattr(s, "hourly_rate", "N/A"), type(getattr(s, "hourly_rate", None)).__name__,
            )

        return specialists
    except Exception as e:
        import traceback
        logger.error("GET /specialists error: %s\n%s", e, traceback.format_exc())
        raise


@router.get("/specialists/{specialist_id}", response_model=SpecialistResponse)
async def get_specialist_by_id(
    specialist_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ FIX #3: Додано GET endpoint для отримання одного спеціаліста за ID
    Повертає 404 якщо спеціаліст не знайдений
    """
    result = await db.execute(
        select(Specialist).where(Specialist.id == specialist_id)
    )
    specialist = result.scalar_one_or_none()
    
    if not specialist:
        raise HTTPException(status_code=404, detail="Specialist not found")
    
    return specialist


@router.put("/specialists/{specialist_id}", response_model=SpecialistResponse)
async def update_specialist(
    specialist_id: int,
    data: SpecialistUpdate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_role("admin", "specialist")),
):
    """Оновлення спеціаліста (admin або specialist)."""
    result = await db.execute(select(Specialist).where(Specialist.id == specialist_id))
    specialist = result.scalar_one_or_none()
    if not specialist:
        raise HTTPException(status_code=404, detail="Specialist not found")
    payload = data.model_dump(exclude_unset=True)
    for key, value in payload.items():
        setattr(specialist, key, value)
    await db.commit()
    await db.refresh(specialist)
    return specialist


@router.delete("/specialists/{specialist_id}")
async def delete_specialist(
    specialist_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_role("admin", "specialist")),
):
    """М'яке видалення: is_active = False (admin або specialist)."""
    result = await db.execute(select(Specialist).where(Specialist.id == specialist_id))
    specialist = result.scalar_one_or_none()
    if not specialist:
        raise HTTPException(status_code=404, detail="Specialist not found")
    specialist.is_active = False
    await db.commit()
    return {"message": "Specialist deactivated", "id": specialist_id}


@router.get("/specialists/search", response_model=SpecialistSearchResult)
async def search_specialists(
    q: str = Query(..., min_length=1),
    specialty: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    """Search specialists by keywords (public). Returns ranked matches with match_reason."""
    matcher = SpecialistMatcher(db, _project_id())
    results = await matcher.search(query=q, specialty=specialty, limit=limit)
    try:
        if results and user:
            rec_svc = RecommendationService(db, _project_id())
            for r in results:
                sid = r.get("id") if isinstance(r, dict) else getattr(r, "id", None)
                if sid:
                    await rec_svc.record_recommendation(
                        specialist_id=int(sid),
                        user_id=user.id,
                        source="search",
                        conversation_id=None,
                    )
            await db.commit()
    except Exception:
        pass
    items = [
        SpecialistMatchItem(
            id=r["id"],
            name=r["name"],
            specialty=r["specialty"],
            description=r.get("description"),
            rating=r.get("rating"),
            contact_link=r.get("contact_link"),
            avatar_url=r.get("avatar_url"),
            match_reason=r.get("match_reason", ""),
        )
        for r in results
    ]
    return SpecialistSearchResult(specialists=items, query=q, total_found=len(items))


@router.get("/specialists/{specialist_id}/details")
async def get_specialist_details(
    specialist_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Full specialist profile (for AI/details page). Public."""
    r = await db.execute(
        select(Specialist).where(Specialist.id == specialist_id, Specialist.is_active == True)
    )
    spec = r.scalar_one_or_none()
    if not spec:
        raise HTTPException(status_code=404, detail="Specialist not found")
    profile_r = await db.execute(
        select(PractitionerProfile).where(
            PractitionerProfile.specialist_id == specialist_id,
            PractitionerProfile.project_id == _project_id(),
        ).limit(1)
    )
    profile = profile_r.scalar_one_or_none()
    return {
        "id": spec.id,
        "name": spec.name,
        "specialty": spec.specialty,
        "service_type": spec.service_type,
        "bio": spec.bio,
        "hourly_rate": spec.hourly_rate,
        "delivery_method": spec.delivery_method,
        "portfolio_url": spec.portfolio_url,
        "telegram_id": spec.telegram_id,
        "unique_story": getattr(profile, "unique_story", None) if profile else None,
        "contact_link": getattr(profile, "contact_link", None) if profile else None,
    }