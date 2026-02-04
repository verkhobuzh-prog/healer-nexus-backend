"""Pydantic schemas for Specialist with backward compatibility: specialty (old) and specialization (new)."""
from __future__ import annotations

from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class SpecialistCreate(BaseModel):
    """Schema for creating specialist. Accepts both 'specialty' (old API) and 'specialization' (new)."""
    name: str = Field(..., min_length=1, max_length=255)
    role: Optional[str] = Field(None, max_length=100)
    specialization: Optional[str] = Field(
        None,
        max_length=255,
        validation_alias=AliasChoices("specialty", "specialization"),
    )
    bio: Optional[str] = None
    is_active: bool = True
    is_ai_powered: bool = False

    model_config = ConfigDict(populate_by_name=True)


class SpecialistResponse(BaseModel):
    """Schema for specialist response. Returns 'specialization' (DB field); serializes as 'specialty' for old clients."""
    id: int
    name: str
    role: Optional[str] = None
    specialization: Optional[str] = Field(None, serialization_alias="specialty")
    bio: Optional[str] = None
    is_active: bool = True
    is_ai_powered: bool = False

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
