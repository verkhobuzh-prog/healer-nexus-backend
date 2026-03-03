"""Pydantic schemas for specialist applications."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
class ApplicationCreate(BaseModel):
    name: str
    specialty: str
    service_type: str = "healer"
    bio: str
    experience_years: int = 0
    motivation: Optional[str] = None
    hourly_rate: int = 0
    contact_telegram: Optional[str] = None
class ApplicationResponse(BaseModel):
    id: int
    user_id: int
    name: str
    specialty: str
    service_type: str
    bio: str
    experience_years: int
    motivation: Optional[str]
    hourly_rate: int
    contact_telegram: Optional[str]
    status: str
    admin_comment: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True
class ApplicationReview(BaseModel):
    status: str  # "approved" or "rejected"
    admin_comment: Optional[str] = None
class RoleUpdate(BaseModel):
    role: str  # "user", "practitioner", "admin"
