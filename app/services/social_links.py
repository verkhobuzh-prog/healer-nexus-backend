"""Social links: URL mapping, validation, rendering."""

SOCIAL_URL_MAP = {
    "telegram": "https://t.me/{username}",
    "instagram": "https://instagram.com/{username}",
    "youtube": "https://youtube.com/{username}",
    "facebook": "https://facebook.com/{username}",
    "tiktok": "https://tiktok.com/@{username}",
    "linkedin": "https://linkedin.com/in/{username}",
    "behance": "https://behance.net/{username}",
    "dribbble": "https://dribbble.com/{username}",
    "twitter": "https://x.com/{username}",
}

SOCIAL_ICONS = {
    "telegram": "✈️",
    "instagram": "📷",
    "youtube": "🎬",
    "facebook": "📘",
    "tiktok": "🎵",
    "linkedin": "💼",
    "behance": "🎨",
    "dribbble": "🏀",
    "twitter": "🐦",
}

SUPPORTED_PLATFORMS = list(SOCIAL_URL_MAP.keys())


def build_social_url(platform: str, username: str) -> str | None:
    """Build full URL from platform name and username."""
    template = SOCIAL_URL_MAP.get(platform.lower())
    if not template or not username:
        return None
    # Strip @ if user added it (except tiktok where we handle it)
    clean = username.strip().lstrip("@")
    return template.format(username=clean)


def build_all_social_urls(social_links: dict | None) -> list[dict]:
    """Convert {platform: username} dict to list of {platform, username, url, icon}."""
    if not social_links:
        return []
    result = []
    for platform, username in social_links.items():
        if not username:
            continue
        url = build_social_url(platform, username)
        if url:
            result.append({
                "platform": platform,
                "username": username,
                "url": url,
                "icon": SOCIAL_ICONS.get(platform, "🔗"),
            })
    return result


def validate_social_links(data: dict) -> dict:
    """Validate and clean social links dict. Remove unknown platforms and empty values."""
    cleaned = {}
    for platform, username in data.items():
        platform_lower = platform.lower().strip()
        if platform_lower in SOCIAL_URL_MAP and username and str(username).strip():
            cleaned[platform_lower] = str(username).strip().lstrip("@")
    return cleaned
