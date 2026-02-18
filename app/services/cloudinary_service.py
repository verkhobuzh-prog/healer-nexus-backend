"""
Cloudinary image upload: lazy config, blog folder, OG and thumbnail transforms.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return
    try:
        import cloudinary
        cloud_name = getattr(settings, "CLOUDINARY_CLOUD_NAME", "") or ""
        api_key = getattr(settings, "CLOUDINARY_API_KEY", "") or ""
        api_secret = getattr(settings, "CLOUDINARY_API_SECRET", "") or ""
        if cloud_name and api_key and api_secret:
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
            )
            _configured = True
        else:
            logger.warning("Cloudinary env vars missing; uploads will fail.")
    except Exception as e:
        logger.warning("Cloudinary configure failed: %s", e)


def upload_image(
    file_data: Any,
    public_id: Optional[str] = None,
    folder: str = "healer-nexus/blog",
    max_width: int = 1200,
) -> dict[str, Any]:
    """
    Upload image with limit crop, auto quality, auto format.
    Returns: url, secure_url, public_id, width, height, og_image_url, thumbnail_url.
    """
    _configure()
    import cloudinary.uploader
    opts: dict[str, Any] = {
        "folder": folder,
        "transformation": [
            {"crop": "limit", "width": max_width},
            {"quality": "auto"},
            {"fetch_format": "auto"},
        ],
    }
    if public_id:
        opts["public_id"] = public_id
    result = cloudinary.uploader.upload(file_data, **opts)
    url = result.get("url") or ""
    secure_url = result.get("secure_url") or url
    pid = result.get("public_id") or ""
    w = result.get("width") or 0
    h = result.get("height") or 0
    # Eager transforms: OG 1200x630, thumbnail 400x300
    base = result.get("secure_url", "").rsplit("/", 1)[0]
    # Build transform URLs (Cloudinary: url/transform/v123/public_id.ext)
    from cloudinary import CloudinaryImage
    img = CloudinaryImage(pid)
    og_url = img.build_url(transformation=[{"width": 1200, "height": 630, "crop": "fill"}])
    thumb_url = img.build_url(transformation=[{"width": 400, "height": 300, "crop": "fill"}])
    return {
        "url": url,
        "secure_url": secure_url,
        "public_id": pid,
        "width": w,
        "height": h,
        "og_image_url": og_url,
        "thumbnail_url": thumb_url,
    }


def delete_image(public_id: str) -> dict[str, Any]:
    _configure()
    import cloudinary.uploader
    return cloudinary.uploader.destroy(public_id)
