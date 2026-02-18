"""
Pydantic v2 schemas for Blog API.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class BlogPostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(default="")
    editor_type: str = Field(default="markdown", description="markdown | wysiwyg")
    featured_image_url: Optional[str] = Field(None, max_length=1000)
    meta_title: Optional[str] = Field(None, max_length=255)
    meta_description: Optional[str] = Field(None, max_length=500)
    telegram_discussion_url: Optional[str] = Field(None, max_length=500)

    model_config = ConfigDict(from_attributes=True)


class BlogPostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = None
    editor_type: Optional[str] = Field(None, description="markdown | wysiwyg")
    featured_image_url: Optional[str] = Field(None, max_length=1000)
    meta_title: Optional[str] = Field(None, max_length=255)
    meta_description: Optional[str] = Field(None, max_length=500)
    telegram_discussion_url: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field(None, description="draft | published | archived")

    model_config = ConfigDict(from_attributes=True)


class AIGenerateDraftRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    language: str = Field(default="uk", description="uk | en | ru")
    tone: str = Field(default="empathetic_expert", description="empathetic_expert | ...")
    word_count: int = Field(default=1000, ge=200, le=5000)


class BlogPostPublish(BaseModel):
    meta_title: Optional[str] = Field(None, max_length=255)
    meta_description: Optional[str] = Field(None, max_length=500)

    model_config = ConfigDict(from_attributes=True)


class PractitionerBrief(BaseModel):
    id: int
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    unique_story: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BlogPostResponse(BaseModel):
    id: int
    project_id: str
    practitioner_id: int
    title: str
    slug: str
    content: str
    editor_type: str
    status: str
    published_at: Optional[datetime] = None
    featured_image_url: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    views_count: int
    telegram_discussion_url: Optional[str] = None
    ai_generated: bool
    ai_prompt_topic: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    practitioner: Optional[PractitionerBrief] = None
    reading_time_minutes: int = 0

    model_config = ConfigDict(from_attributes=True)


class BlogPostListItem(BaseModel):
    id: int
    project_id: str
    practitioner_id: int
    title: str
    slug: str
    editor_type: str
    status: str
    published_at: Optional[datetime] = None
    featured_image_url: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    views_count: int
    telegram_discussion_url: Optional[str] = None
    ai_generated: bool
    created_at: datetime
    updated_at: datetime
    practitioner: Optional[PractitionerBrief] = None
    reading_time_minutes: int = 0

    model_config = ConfigDict(from_attributes=True)


class BlogPostListResponse(BaseModel):
    items: list[BlogPostListItem]
    total: int
    page: int
    page_size: int
    has_next: bool

    model_config = ConfigDict(from_attributes=True)


class AIGenerateDraftResponse(BaseModel):
    title: str
    content: str
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    ai_prompt_topic: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
