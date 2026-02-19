"""
Booking API: create, list, confirm, cancel. Prefix /api/bookings.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.specialist import Specialist
from app.models.booking import Booking
from app.schemas.booking import BookingCreate, BookingResponse, BookingListResponse
from app.services.booking_service import BookingService
from app.config import settings

router = APIRouter(prefix="/api/bookings", tags=["Bookings"])


def _project_id() -> str:
    return getattr(settings, "PROJECT_ID", "healer_nexus")


async def _user_id_from_header(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
) -> int:
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    try:
        return int(x_user_id.strip())
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid X-User-Id")


async def _specialist_id_from_header(
    x_specialist_id: Optional[str] = Header(None, alias="X-Specialist-Id"),
) -> int:
    if not x_specialist_id or not x_specialist_id.strip():
        raise HTTPException(status_code=401, detail="Missing X-Specialist-Id header")
    try:
        return int(x_specialist_id.strip())
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid X-Specialist-Id")


def _booking_to_response(booking: Booking, specialist_name: Optional[str] = None, specialist_specialty: Optional[str] = None) -> BookingResponse:
    return BookingResponse(
        id=booking.id,
        project_id=booking.project_id,
        user_id=booking.user_id,
        specialist_id=booking.specialist_id,
        specialist_name=specialist_name,
        specialist_specialty=specialist_specialty,
        status=booking.status,
        reason=booking.reason,
        user_message=booking.user_message,
        contact_method=booking.contact_method,
        telegram_notified=booking.telegram_notified,
        scheduled_at=booking.scheduled_at,
        confirmed_at=booking.confirmed_at,
        created_at=booking.created_at,
    )


@router.get("/", response_model=BookingListResponse)
async def list_my_bookings(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(_user_id_from_header),
):
    """List current user's bookings (requires X-User-Id)."""
    svc = BookingService(db, _project_id())
    bookings, total = await svc.list_bookings(user_id=user_id, status=status, page=page, page_size=page_size)
    specialists = {}
    if bookings:
        r = await db.execute(select(Specialist).where(Specialist.id.in_(b.specialist_id for b in bookings)))
        for s in r.scalars().all():
            specialists[s.id] = (s.name, s.specialty)
    items = [
        _booking_to_response(
            b,
            specialist_name=specialists.get(b.specialist_id, (None, None))[0],
            specialist_specialty=specialists.get(b.specialist_id, (None, None))[1],
        )
        for b in bookings
    ]
    return BookingListResponse(items=items, total=total)


@router.get("/specialist", response_model=BookingListResponse)
async def list_specialist_bookings(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    specialist_id: int = Depends(_specialist_id_from_header),
):
    """List bookings for the given specialist (requires X-Specialist-Id)."""
    svc = BookingService(db, _project_id())
    bookings, total = await svc.list_bookings(specialist_id=specialist_id, status=status, page=page, page_size=page_size)
    r = await db.execute(select(Specialist).where(Specialist.id == specialist_id))
    spec = r.scalar_one_or_none()
    name, specialty = (spec.name, spec.specialty) if spec else (None, None)
    items = [_booking_to_response(b, specialist_name=name, specialist_specialty=specialty) for b in bookings]
    return BookingListResponse(items=items, total=total)


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(_user_id_from_header),
):
    """Get booking by id (owner only)."""
    svc = BookingService(db, _project_id())
    booking = await svc.get_booking(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.user_id != user_id:
        raise HTTPException(status_code=404, detail="Booking not found")
    r = await db.execute(select(Specialist).where(Specialist.id == booking.specialist_id))
    spec = r.scalar_one_or_none()
    return _booking_to_response(
        booking,
        specialist_name=spec.name if spec else None,
        specialist_specialty=spec.specialty if spec else None,
    )


@router.post("/", response_model=BookingResponse, status_code=201)
async def create_booking(
    body: BookingCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(_user_id_from_header),
):
    """Create a booking (requires X-User-Id)."""
    svc = BookingService(db, _project_id())
    try:
        booking = await svc.create_booking(
            user_id=user_id,
            specialist_id=body.specialist_id,
            reason=body.reason,
            user_message=body.user_message,
            contact_method=body.contact_method,
            scheduled_at=body.scheduled_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    r = await db.execute(select(Specialist).where(Specialist.id == booking.specialist_id))
    spec = r.scalar_one_or_none()
    return _booking_to_response(
        booking,
        specialist_name=spec.name if spec else None,
        specialist_specialty=spec.specialty if spec else None,
    )


@router.post("/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(_user_id_from_header),
):
    """Cancel a booking (owner only)."""
    svc = BookingService(db, _project_id())
    booking = await svc.get_booking(booking_id)
    if not booking or booking.user_id != user_id:
        raise HTTPException(status_code=404, detail="Booking not found")
    updated = await svc.cancel_booking(booking_id)
    if not updated:
        raise HTTPException(status_code=400, detail="Booking cannot be cancelled")
    r = await db.execute(select(Specialist).where(Specialist.id == updated.specialist_id))
    spec = r.scalar_one_or_none()
    return _booking_to_response(
        updated,
        specialist_name=spec.name if spec else None,
        specialist_specialty=spec.specialty if spec else None,
    )


# Specialist-facing: confirm / complete (auth by X-Specialist-Id)

@router.post("/{booking_id}/confirm", response_model=BookingResponse)
async def confirm_booking(
    booking_id: int,
    specialist_notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    specialist_id: int = Depends(_specialist_id_from_header),
):
    """Confirm a booking (specialist only)."""
    svc = BookingService(db, _project_id())
    booking = await svc.get_booking(booking_id)
    if not booking or booking.specialist_id != specialist_id:
        raise HTTPException(status_code=404, detail="Booking not found")
    updated = await svc.confirm_booking(booking_id, specialist_notes=specialist_notes)
    if not updated:
        raise HTTPException(status_code=400, detail="Booking cannot be confirmed")
    r = await db.execute(select(Specialist).where(Specialist.id == specialist_id))
    spec = r.scalar_one_or_none()
    return _booking_to_response(
        updated,
        specialist_name=spec.name if spec else None,
        specialist_specialty=spec.specialty if spec else None,
    )


@router.post("/{booking_id}/complete", response_model=BookingResponse)
async def complete_booking(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    specialist_id: int = Depends(_specialist_id_from_header),
):
    """Mark booking as completed (specialist only)."""
    svc = BookingService(db, _project_id())
    booking = await svc.get_booking(booking_id)
    if not booking or booking.specialist_id != specialist_id:
        raise HTTPException(status_code=404, detail="Booking not found")
    updated = await svc.complete_booking(booking_id)
    if not updated:
        raise HTTPException(status_code=400, detail="Booking cannot be completed")
    r = await db.execute(select(Specialist).where(Specialist.id == specialist_id))
    spec = r.scalar_one_or_none()
    return _booking_to_response(
        updated,
        specialist_name=spec.name if spec else None,
        specialist_specialty=spec.specialty if spec else None,
    )
