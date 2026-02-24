"""SEO: sitemap.xml and robots.txt."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.practitioner_profile import PractitionerProfile
from app.models.blog_post import BlogPost
from app.config import settings

router = APIRouter(tags=["SEO"])


@router.get("/sitemap.xml", response_class=Response)
async def sitemap_xml(db: AsyncSession = Depends(get_db)):
    """Dynamic sitemap with all specialists (by slug or id) and published blog posts."""
    base = settings.BASE_URL.rstrip("/")
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")

    # Active practitioner profiles (for /specialists/ and /blog/)
    r = await db.execute(
        select(PractitionerProfile)
        .where(
            PractitionerProfile.project_id == project_id,
            PractitionerProfile.is_active == True,
        )
    )
    profiles = list(r.scalars().all())

    # Published posts with practitioner_id
    r2 = await db.execute(
        select(BlogPost)
        .where(
            BlogPost.project_id == project_id,
            BlogPost.status == "published",
        )
    )
    posts = list(r2.scalars().all())
    profile_ids = {p.id for p in profiles}
    profile_by_id = {p.id: p for p in profiles}
    posts = [p for p in posts if p.practitioner_id in profile_ids]

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for p in profiles:
        loc = f"{base}/specialists/{(p.slug or str(p.id))}"
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append("    <changefreq>weekly</changefreq>")
        lines.append("  </url>")
        # Blog index for this practitioner
        blog_loc = f"{base}/blog/{(p.slug or str(p.id))}"
        lines.append("  <url>")
        lines.append(f"    <loc>{blog_loc}</loc>")
        lines.append("    <changefreq>weekly</changefreq>")
        lines.append("  </url>")
    for post in posts:
        prof = profile_by_id.get(post.practitioner_id)
        if not prof:
            continue
        practitioner_slug = prof.slug or str(prof.id)
        loc = f"{base}/blog/{practitioner_slug}/{post.slug}"
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append("    <changefreq>monthly</changefreq>")
        if post.published_at:
            lines.append(f"    <lastmod>{post.published_at.strftime('%Y-%m-%d')}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    xml = "\n".join(lines)
    return Response(content=xml, media_type="application/xml")


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    """Allow /specialists/ and /blog/, disallow /api/ and /docs/."""
    base = settings.BASE_URL.rstrip("/")
    lines = [
        "User-agent: *",
        "Allow: /specialists/",
        "Allow: /blog/",
        "Allow: /",
        "Disallow: /api/",
        "Disallow: /docs",
        "",
        f"Sitemap: {base}/sitemap.xml",
    ]
    return "\n".join(lines)
