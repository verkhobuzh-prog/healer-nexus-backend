"""Social links schemas for practitioner profiles."""
from __future__ import annotations

from pydantic import BaseModel


class SocialLinksUpdate(BaseModel):
    """Update social links. Send only the platforms you want to set/change."""

    telegram_channel_id: str | None = None  # Telegram channel/chat ID for blog announcements (PractitionerProfile.telegram_channel_id)
    telegram: str | None = None
    instagram: str | None = None
    youtube: str | None = None
    facebook: str | None = None
    tiktok: str | None = None
    linkedin: str | None = None
    behance: str | None = None
    dribbble: str | None = None
    twitter: str | None = None


class SocialLinkItem(BaseModel):
    platform: str
    username: str
    url: str
    icon: str


class SocialLinksResponse(BaseModel):
    links: list[SocialLinkItem]
    supported_platforms: list[str]
    telegram_channel_id: str | None = None
