"""
Pydantic v2 schemas for Blog Categories and Tags.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict


# --- Category ---
class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = None
    parent_id: int | None = None
    icon_emoji: str | None = Field(None, max_length=10)
    sort_order: int = 0

    model_config = ConfigDict(from_attributes=True)


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = None
    parent_id: int | None = None
    icon_emoji: str | None = Field(None, max_length=10)
    sort_order: int | None = None
    is_active: bool | None = None

    model_config = ConfigDict(from_attributes=True)


class CategoryResponse(BaseModel):
    id: int
    project_id: str
    name: str
    slug: str
    description: str | None
    parent_id: int | None
    icon_emoji: str | None
    sort_order: int
    is_active: bool
    post_count: int = 0
    children: list["CategoryResponse"] = []

    model_config = ConfigDict(from_attributes=True)


class CategoryTreeResponse(BaseModel):
    categories: list[CategoryResponse]

    model_config = ConfigDict(from_attributes=True)


# --- Tag ---
class TagCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)

    model_config = ConfigDict(from_attributes=True)


class TagResponse(BaseModel):
    id: int
    project_id: str
    name: str
    slug: str
    usage_count: int

    model_config = ConfigDict(from_attributes=True)


class TagListResponse(BaseModel):
    items: list[TagResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)


class TagCloudItem(BaseModel):
    name: str
    slug: str
    usage_count: int
    weight: int  # 1-5 scale for font size in tag cloud

    model_config = ConfigDict(from_attributes=True)
