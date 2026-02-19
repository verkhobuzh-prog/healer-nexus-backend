"""
Pydantic schemas for bookings and specialist search results.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BookingCreate(BaseModel):
    specialist_id: int
    reason: str | None = None
    user_message: str | None = None
    contact_method: str = "telegram"
    scheduled_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class BookingResponse(BaseModel):
    id: int
    project_id: str
    user_id: int
    specialist_id: int
    specialist_name: str | None = None
    specialist_specialty: str | None = None
    status: str
    reason: str | None
    user_message: str | None
    contact_method: str
    telegram_notified: bool
    scheduled_at: datetime | None
    confirmed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookingListResponse(BaseModel):
    items: list[BookingResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)


class SpecialistMatchItem(BaseModel):
    id: int
    name: str
    specialty: str
    description: str | None
    rating: float | None
    contact_link: str | None
    avatar_url: str | None
    match_reason: str

    model_config = ConfigDict(from_attributes=True)


class SpecialistSearchResult(BaseModel):
    specialists: list[SpecialistMatchItem]
    query: str
    total_found: int

    model_config = ConfigDict(from_attributes=True)
