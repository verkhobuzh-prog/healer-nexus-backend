"""
Blog analytics: view recording, daily aggregation, post/practitioner stats.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func, update, delete, case, and_, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.blog_post import BlogPost, PostStatus
from app.models.blog_post_view import BlogPostView
from app.models.blog_analytics_daily import BlogAnalyticsDaily
from app.schemas.blog_analytics import (
    PostAnalytics,
    DailyViewStats,
    ReferrerStats,
    BlogDashboardStats,
    PopularPostItem,
    TrendingPostItem,
)


def _parse_referrer_source(referrer_url: Optional[str]) -> str:
    if not referrer_url or not referrer_url.strip():
        return "direct"
    u = referrer_url.strip().lower()
    if "telegram.me" in u or "t.me" in u:
        return "telegram"
    if "google." in u or "google.com" in u:
        return "google"
    if "facebook." in u or "fb." in u or "fb.com" in u or "facebook.com" in u:
        return "facebook"
    if "t.co" in u or "twitter." in u:
        return "twitter"
    return "other"


def _parse_device_type(user_agent: Optional[str]) -> str:
    if not user_agent or not user_agent.strip():
        return "desktop"
    ua = user_agent.strip()
    if "Mobile" in ua and "Tablet" not in ua:
        return "mobile"
    if "Tablet" in ua:
        return "tablet"
    return "desktop"


def _hash_ip(ip_address: Optional[str]) -> Optional[str]:
    if not ip_address or not ip_address.strip():
        return None
    return hashlib.sha256(ip_address.strip().encode()).hexdigest()


class BlogAnalyticsService:
    def __init__(self, session: AsyncSession, project_id: str):
        self.session = session
        self.project_id = project_id

    async def record_view(
        self,
        post_id: int,
        referrer_url: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        referrer_source = _parse_referrer_source(referrer_url)
        device_type = _parse_device_type(user_agent)
        ip_hash = _hash_ip(ip_address)
        viewed_at = datetime.now(timezone.utc)
        # Truncate long strings to column limits
        ref_url = (referrer_url or "")[:500] if referrer_url else None
        ua = (user_agent or "")[:500] if user_agent else None
        sid = (session_id or "")[:64] if session_id else None

        self.session.add(
            BlogPostView(
                post_id=post_id,
                project_id=self.project_id,
                viewed_at=viewed_at,
                referrer_url=ref_url,
                referrer_source=referrer_source,
                user_agent=ua,
                device_type=device_type,
                ip_hash=ip_hash,
                session_id=sid,
            )
        )
        await self.session.execute(
            update(BlogPost)
            .where(
                and_(BlogPost.id == post_id, BlogPost.project_id == self.project_id)
            )
            .values(views_count=BlogPost.views_count + 1)
        )
        await self.session.commit()

    async def aggregate_daily(self, target_date: date) -> None:
        # Compare DATE to date object (PostgreSQL strict: no date = varchar)
        # Get post_ids that have views on target_date
        q = (
            select(BlogPostView.post_id)
            .where(
                BlogPostView.project_id == self.project_id,
                func.date(BlogPostView.viewed_at) == target_date,
            )
            .distinct()
        )
        r = await self.session.execute(q)
        post_ids = [row[0] for row in r.fetchall()]
        if not post_ids:
            return

        for post_id in post_ids:
            # Aggregate this post's views on target_date
            base = select(
                BlogPostView.post_id,
                func.count().label("views_total"),
                func.count(distinct(BlogPostView.ip_hash)).label("views_unique"),
                func.sum(
                    case((BlogPostView.referrer_source == "telegram", 1), else_=0)
                ).label("r_telegram"),
                func.sum(
                    case((BlogPostView.referrer_source == "facebook", 1), else_=0)
                ).label("r_facebook"),
                func.sum(
                    case((BlogPostView.referrer_source == "twitter", 1), else_=0)
                ).label("r_twitter"),
                func.sum(
                    case((BlogPostView.referrer_source == "google", 1), else_=0)
                ).label("r_google"),
                func.sum(
                    case((BlogPostView.referrer_source == "direct", 1), else_=0)
                ).label("r_direct"),
                func.sum(
                    case((BlogPostView.referrer_source == "other", 1), else_=0)
                ).label("r_other"),
            ).where(
                BlogPostView.project_id == self.project_id,
                BlogPostView.post_id == post_id,
                func.date(BlogPostView.viewed_at) == target_date,
            )
            agg = await self.session.execute(base)
            row = agg.one()
            views_total = row.views_total or 0
            views_unique = row.views_unique or 0
            r_telegram = int(row.r_telegram or 0)
            r_facebook = int(row.r_facebook or 0)
            r_twitter = int(row.r_twitter or 0)
            r_google = int(row.r_google or 0)
            r_direct = int(row.r_direct or 0)
            r_other = int(row.r_other or 0)

            # Upsert: select existing or insert
            existing = await self.session.execute(
                select(BlogAnalyticsDaily).where(
                    BlogAnalyticsDaily.post_id == post_id,
                    BlogAnalyticsDaily.date == target_date,
                )
            )
            rec = existing.scalar_one_or_none()
            if rec:
                rec.views_total = views_total
                rec.views_unique = views_unique
                rec.referrer_telegram = r_telegram
                rec.referrer_facebook = r_facebook
                rec.referrer_twitter = r_twitter
                rec.referrer_google = r_google
                rec.referrer_direct = r_direct
                rec.referrer_other = r_other
            else:
                self.session.add(
                    BlogAnalyticsDaily(
                        post_id=post_id,
                        project_id=self.project_id,
                        date=target_date,
                        views_total=views_total,
                        views_unique=views_unique,
                        referrer_telegram=r_telegram,
                        referrer_facebook=r_facebook,
                        referrer_twitter=r_twitter,
                        referrer_google=r_google,
                        referrer_direct=r_direct,
                        referrer_other=r_other,
                    )
                )
        await self.session.commit()

    async def get_post_analytics(
        self, post_id: int, practitioner_id: Optional[int] = None
    ) -> Optional[PostAnalytics]:
        q = select(BlogPost).where(
            BlogPost.id == post_id,
            BlogPost.project_id == self.project_id,
        )
        if practitioner_id is not None:
            q = q.where(BlogPost.practitioner_id == practitioner_id)
        r = await self.session.execute(q)
        post = r.scalar_one_or_none()
        if not post:
            return None

        today = date.today()
        start_7d = today - timedelta(days=7)
        start_30d = today - timedelta(days=30)

        # From blog_analytics_daily
        q_totals = (
            select(
                func.coalesce(func.sum(BlogAnalyticsDaily.views_total), 0).label("total"),
                func.coalesce(func.sum(BlogAnalyticsDaily.views_unique), 0).label("unique"),
            )
            .where(
                BlogAnalyticsDaily.post_id == post_id,
                BlogAnalyticsDaily.project_id == self.project_id,
            )
        )
        r_totals = await self.session.execute(q_totals)
        tot_row = r_totals.one()
        total_views = int(tot_row.total or 0)
        total_unique = int(tot_row.unique or 0)

        q_today = (
            select(
                func.coalesce(func.sum(BlogAnalyticsDaily.views_total), 0).label("v"),
            )
            .where(
                BlogAnalyticsDaily.post_id == post_id,
                BlogAnalyticsDaily.project_id == self.project_id,
                BlogAnalyticsDaily.date == today,
            )
        )
        r_today = await self.session.execute(q_today)
        views_today = int((r_today.scalar() or 0))

        q_7d = (
            select(func.coalesce(func.sum(BlogAnalyticsDaily.views_total), 0).label("v"))
            .where(
                BlogAnalyticsDaily.post_id == post_id,
                BlogAnalyticsDaily.project_id == self.project_id,
                BlogAnalyticsDaily.date >= start_7d,
                BlogAnalyticsDaily.date <= today,
            )
        )
        r_7d = await self.session.execute(q_7d)
        views_7d = int((r_7d.scalar() or 0))

        q_30d = (
            select(func.coalesce(func.sum(BlogAnalyticsDaily.views_total), 0).label("v"))
            .where(
                BlogAnalyticsDaily.post_id == post_id,
                BlogAnalyticsDaily.project_id == self.project_id,
                BlogAnalyticsDaily.date >= start_30d,
                BlogAnalyticsDaily.date <= today,
            )
        )
        r_30d = await self.session.execute(q_30d)
        views_30d = int((r_30d.scalar() or 0))

        avg_daily_views = (views_30d / 30.0) if views_30d else 0.0

        # Top referrer
        q_ref = (
            select(BlogAnalyticsDaily)
            .where(
                BlogAnalyticsDaily.post_id == post_id,
                BlogAnalyticsDaily.project_id == self.project_id,
                BlogAnalyticsDaily.date >= start_30d,
            )
        )
        ref_rows = await self.session.execute(q_ref)
        ref_rows = ref_rows.scalars().all()
        ref_counts = {
            "telegram": 0,
            "facebook": 0,
            "twitter": 0,
            "google": 0,
            "direct": 0,
            "other": 0,
        }
        for row in ref_rows:
            ref_counts["telegram"] += row.referrer_telegram
            ref_counts["facebook"] += row.referrer_facebook
            ref_counts["twitter"] += row.referrer_twitter
            ref_counts["google"] += row.referrer_google
            ref_counts["direct"] += row.referrer_direct
            ref_counts["other"] += row.referrer_other
        top_referrer = max(ref_counts, key=ref_counts.get) if ref_counts else "direct"

        # Trend: last 7d vs previous 7d
        start_14d = today - timedelta(days=14)
        q_curr_7 = (
            select(func.coalesce(func.sum(BlogAnalyticsDaily.views_total), 0).label("v"))
            .where(
                BlogAnalyticsDaily.post_id == post_id,
                BlogAnalyticsDaily.project_id == self.project_id,
                BlogAnalyticsDaily.date >= start_7d,
                BlogAnalyticsDaily.date <= today,
            )
        )
        q_prev_7 = (
            select(func.coalesce(func.sum(BlogAnalyticsDaily.views_total), 0).label("v"))
            .where(
                BlogAnalyticsDaily.post_id == post_id,
                BlogAnalyticsDaily.project_id == self.project_id,
                BlogAnalyticsDaily.date >= start_14d,
                BlogAnalyticsDaily.date < start_7d,
            )
        )
        r_curr = await self.session.execute(q_curr_7)
        r_prev = await self.session.execute(q_prev_7)
        curr_7 = int(r_curr.scalar() or 0)
        prev_7 = int(r_prev.scalar() or 0)
        if prev_7 == 0:
            trend = "up" if curr_7 > 0 else "stable"
            trend_percent = 100.0 if curr_7 > 0 else 0.0
        else:
            change_pct = ((curr_7 - prev_7) / prev_7) * 100
            trend = "up" if change_pct > 5 else ("down" if change_pct < -5 else "stable")
            trend_percent = change_pct

        return PostAnalytics(
            post_id=post.id,
            post_title=post.title,
            post_slug=post.slug,
            total_views=total_views,
            unique_views=total_unique,
            views_today=views_today,
            views_7d=views_7d,
            views_30d=views_30d,
            avg_daily_views=round(avg_daily_views, 2),
            top_referrer=top_referrer,
            trend=trend,
            trend_percent=round(trend_percent, 2),
        )

    async def get_post_daily_views(
        self,
        post_id: int,
        days: int = 30,
        practitioner_id: Optional[int] = None,
    ) -> list[DailyViewStats]:
        if practitioner_id is not None:
            r = await self.session.execute(
                select(BlogPost.id).where(
                    BlogPost.id == post_id,
                    BlogPost.project_id == self.project_id,
                    BlogPost.practitioner_id == practitioner_id,
                )
            )
            if r.scalar_one_or_none() is None:
                return []
        end = date.today()
        start = end - timedelta(days=days - 1)
        q = (
            select(
                BlogAnalyticsDaily.date,
                BlogAnalyticsDaily.views_total,
                BlogAnalyticsDaily.views_unique,
            )
            .where(
                BlogAnalyticsDaily.post_id == post_id,
                BlogAnalyticsDaily.project_id == self.project_id,
                BlogAnalyticsDaily.date >= start,
                BlogAnalyticsDaily.date <= end,
            )
            .order_by(BlogAnalyticsDaily.date)
        )
        r = await self.session.execute(q)
        return [
            DailyViewStats(date=row.date, views_total=row.views_total, views_unique=row.views_unique)
            for row in r.fetchall()
        ]

    async def get_post_referrers(
        self,
        post_id: int,
        days: int = 30,
        practitioner_id: Optional[int] = None,
    ) -> list[ReferrerStats]:
        if practitioner_id is not None:
            r = await self.session.execute(
                select(BlogPost.id).where(
                    BlogPost.id == post_id,
                    BlogPost.project_id == self.project_id,
                    BlogPost.practitioner_id == practitioner_id,
                )
            )
            if r.scalar_one_or_none() is None:
                return [
                    ReferrerStats(source=s, count=0, percent=0.0)
                    for s in ["telegram", "google", "facebook", "twitter", "direct", "other"]
                ]
        start = date.today() - timedelta(days=days - 1)
        q = (
            select(BlogAnalyticsDaily)
            .where(
                BlogAnalyticsDaily.post_id == post_id,
                BlogAnalyticsDaily.project_id == self.project_id,
                BlogAnalyticsDaily.date >= start,
            )
        )
        r = await self.session.execute(q)
        rows = r.scalars().all()
        total = 0
        counts = {"telegram": 0, "facebook": 0, "twitter": 0, "google": 0, "direct": 0, "other": 0}
        for row in rows:
            total += row.referrer_telegram + row.referrer_facebook + row.referrer_twitter
            total += row.referrer_google + row.referrer_direct + row.referrer_other
            counts["telegram"] += row.referrer_telegram
            counts["facebook"] += row.referrer_facebook
            counts["twitter"] += row.referrer_twitter
            counts["google"] += row.referrer_google
            counts["direct"] += row.referrer_direct
            counts["other"] += row.referrer_other
        if total == 0:
            return [
                ReferrerStats(source=s, count=0, percent=0.0)
                for s in ["telegram", "google", "facebook", "twitter", "direct", "other"]
            ]
        return [
            ReferrerStats(
                source=src,
                count=counts[src],
                percent=round((counts[src] / total) * 100, 2),
            )
            for src in ["telegram", "google", "facebook", "twitter", "direct", "other"]
        ]

    async def get_dashboard_stats(
        self, practitioner_id: int
    ) -> BlogDashboardStats:
        q = select(BlogPost).where(
            BlogPost.project_id == self.project_id,
            BlogPost.practitioner_id == practitioner_id,
        )
        r = await self.session.execute(q)
        posts = list(r.scalars().all())
        total_posts = len(posts)
        published_posts = sum(1 for p in posts if p.status == PostStatus.PUBLISHED.value)
        draft_posts = sum(1 for p in posts if p.status == PostStatus.DRAFT.value)
        scheduled_posts = sum(1 for p in posts if p.status == PostStatus.SCHEDULED.value)

        post_ids = [p.id for p in posts]
        if not post_ids:
            return BlogDashboardStats(
                total_posts=0,
                published_posts=0,
                draft_posts=0,
                scheduled_posts=0,
                total_views=0,
                total_unique_views=0,
                views_today=0,
                views_7d=0,
                views_30d=0,
                avg_daily_views=0.0,
            )

        today = date.today()
        start_7d = today - timedelta(days=7)
        start_30d = today - timedelta(days=30)

        q_totals = (
            select(
                func.coalesce(func.sum(BlogAnalyticsDaily.views_total), 0).label("total"),
                func.coalesce(func.sum(BlogAnalyticsDaily.views_unique), 0).label("unique"),
            )
            .where(
                BlogAnalyticsDaily.project_id == self.project_id,
                BlogAnalyticsDaily.post_id.in_(post_ids),
            )
        )
        rt = await self.session.execute(q_totals)
        tr = rt.one()
        total_views = int(tr.total or 0)
        total_unique_views = int(tr.unique or 0)

        q_today = (
            select(func.coalesce(func.sum(BlogAnalyticsDaily.views_total), 0).label("v"))
            .where(
                BlogAnalyticsDaily.project_id == self.project_id,
                BlogAnalyticsDaily.post_id.in_(post_ids),
                BlogAnalyticsDaily.date == today,
            )
        )
        q_7d = (
            select(func.coalesce(func.sum(BlogAnalyticsDaily.views_total), 0).label("v"))
            .where(
                BlogAnalyticsDaily.project_id == self.project_id,
                BlogAnalyticsDaily.post_id.in_(post_ids),
                BlogAnalyticsDaily.date >= start_7d,
                BlogAnalyticsDaily.date <= today,
            )
        )
        q_30d = (
            select(func.coalesce(func.sum(BlogAnalyticsDaily.views_total), 0).label("v"))
            .where(
                BlogAnalyticsDaily.project_id == self.project_id,
                BlogAnalyticsDaily.post_id.in_(post_ids),
                BlogAnalyticsDaily.date >= start_30d,
                BlogAnalyticsDaily.date <= today,
            )
        )
        v_today = int((await self.session.execute(q_today)).scalar() or 0)
        v_7d = int((await self.session.execute(q_7d)).scalar() or 0)
        v_30d = int((await self.session.execute(q_30d)).scalar() or 0)
        avg_daily = (v_30d / 30.0) if v_30d else 0.0

        return BlogDashboardStats(
            total_posts=total_posts,
            published_posts=published_posts,
            draft_posts=draft_posts,
            scheduled_posts=scheduled_posts,
            total_views=total_views,
            total_unique_views=total_unique_views,
            views_today=v_today,
            views_7d=v_7d,
            views_30d=v_30d,
            avg_daily_views=round(avg_daily, 2),
        )

    async def get_popular_posts(
        self,
        practitioner_id: Optional[int] = None,
        period: str = "30d",
        limit: int = 10,
    ) -> list[PopularPostItem]:
        today = date.today()
        if period == "7d":
            start = today - timedelta(days=7)
        elif period == "all":
            start = date(2000, 1, 1)
        else:
            start = today - timedelta(days=30)

        q = (
            select(BlogPost)
            .where(
                BlogPost.project_id == self.project_id,
                BlogPost.status == PostStatus.PUBLISHED.value,
            )
            .options(
                selectinload(BlogPost.category),
            )
        )
        if practitioner_id is not None:
            q = q.where(BlogPost.practitioner_id == practitioner_id)
        posts_r = await self.session.execute(q)
        posts = list(posts_r.scalars().all())
        if not posts:
            return []

        post_ids = [p.id for p in posts]
        if period == "all":
            q_agg = (
                select(
                    BlogAnalyticsDaily.post_id,
                    func.sum(BlogAnalyticsDaily.views_total).label("views"),
                    func.sum(BlogAnalyticsDaily.views_unique).label("unique_views"),
                )
                .where(
                    BlogAnalyticsDaily.project_id == self.project_id,
                    BlogAnalyticsDaily.post_id.in_(post_ids),
                )
                .group_by(BlogAnalyticsDaily.post_id)
            )
        else:
            q_agg = (
                select(
                    BlogAnalyticsDaily.post_id,
                    func.sum(BlogAnalyticsDaily.views_total).label("views"),
                    func.sum(BlogAnalyticsDaily.views_unique).label("unique_views"),
                )
                .where(
                    BlogAnalyticsDaily.project_id == self.project_id,
                    BlogAnalyticsDaily.post_id.in_(post_ids),
                    BlogAnalyticsDaily.date >= start,
                    BlogAnalyticsDaily.date <= today,
                )
                .group_by(BlogAnalyticsDaily.post_id)
            )
        r_agg = await self.session.execute(q_agg)
        agg_map = {row.post_id: (int(row.views or 0), int(row.unique_views or 0)) for row in r_agg.fetchall()}
        post_views = [
            (p, agg_map.get(p.id, (0, 0))[0], agg_map.get(p.id, (0, 0))[1])
            for p in posts
        ]
        post_views.sort(key=lambda x: x[1], reverse=True)
        post_views = post_views[:limit]
        return [
            PopularPostItem(
                post_id=p.id,
                title=p.title,
                slug=p.slug,
                views=views,
                unique_views=unique_views,
                published_at=p.published_at,
                featured_image_url=p.featured_image_url,
                category_name=p.category.name if p.category else None,
            )
            for p, views, unique_views in post_views
        ]

    async def get_trending_posts(
        self,
        practitioner_id: Optional[int] = None,
        limit: int = 5,
    ) -> list[TrendingPostItem]:
        today = date.today()
        start_curr = today - timedelta(days=7)
        start_prev = today - timedelta(days=14)
        q = (
            select(BlogPost)
            .where(
                BlogPost.project_id == self.project_id,
                BlogPost.status == PostStatus.PUBLISHED.value,
            )
        )
        if practitioner_id is not None:
            q = q.where(BlogPost.practitioner_id == practitioner_id)
        r = await self.session.execute(q)
        posts = list(r.scalars().all())
        if not posts:
            return []
        post_ids = [p.id for p in posts]

        # Current 7d and previous 7d per post
        q_curr = (
            select(
                BlogAnalyticsDaily.post_id,
                func.coalesce(func.sum(BlogAnalyticsDaily.views_total), 0).label("v"),
            )
            .where(
                BlogAnalyticsDaily.project_id == self.project_id,
                BlogAnalyticsDaily.post_id.in_(post_ids),
                BlogAnalyticsDaily.date >= start_curr,
                BlogAnalyticsDaily.date <= today,
            )
            .group_by(BlogAnalyticsDaily.post_id)
        )
        q_prev = (
            select(
                BlogAnalyticsDaily.post_id,
                func.coalesce(func.sum(BlogAnalyticsDaily.views_total), 0).label("v"),
            )
            .where(
                BlogAnalyticsDaily.project_id == self.project_id,
                BlogAnalyticsDaily.post_id.in_(post_ids),
                BlogAnalyticsDaily.date >= start_prev,
                BlogAnalyticsDaily.date < start_curr,
            )
            .group_by(BlogAnalyticsDaily.post_id)
        )
        r_curr = await self.session.execute(q_curr)
        r_prev = await self.session.execute(q_prev)
        curr_map = {row.post_id: int(row.v or 0) for row in r_curr.fetchall()}
        prev_map = {row.post_id: int(row.v or 0) for row in r_prev.fetchall()}

        result = []
        for p in posts:
            curr = curr_map.get(p.id, 0)
            prev = prev_map.get(p.id, 0)
            if curr < 5:
                continue
            growth = ((curr - prev) / prev * 100) if prev else 100.0
            result.append(
                TrendingPostItem(
                    post_id=p.id,
                    title=p.title,
                    slug=p.slug,
                    views_current_period=curr,
                    views_previous_period=prev,
                    growth_percent=round(growth, 2),
                    featured_image_url=p.featured_image_url,
                )
            )
        result.sort(key=lambda x: x.growth_percent, reverse=True)
        return result[:limit]

    async def get_dashboard_daily_views(
        self, practitioner_id: int, days: int = 30
    ) -> list[DailyViewStats]:
        """Daily view totals across all posts of a practitioner."""
        post_ids_r = await self.session.execute(
            select(BlogPost.id).where(
                BlogPost.project_id == self.project_id,
                BlogPost.practitioner_id == practitioner_id,
            )
        )
        post_ids = [r[0] for r in post_ids_r.fetchall()]
        if not post_ids:
            return []
        end = date.today()
        start = end - timedelta(days=days - 1)
        q = (
            select(
                BlogAnalyticsDaily.date,
                func.sum(BlogAnalyticsDaily.views_total).label("views_total"),
                func.sum(BlogAnalyticsDaily.views_unique).label("views_unique"),
            )
            .where(
                BlogAnalyticsDaily.project_id == self.project_id,
                BlogAnalyticsDaily.post_id.in_(post_ids),
                BlogAnalyticsDaily.date >= start,
                BlogAnalyticsDaily.date <= end,
            )
            .group_by(BlogAnalyticsDaily.date)
            .order_by(BlogAnalyticsDaily.date)
        )
        r = await self.session.execute(q)
        return [
            DailyViewStats(date=row.date, views_total=int(row.views_total or 0), views_unique=int(row.views_unique or 0))
            for row in r.fetchall()
        ]

    async def get_referrer_breakdown(
        self,
        practitioner_id: Optional[int] = None,
        days: int = 30,
    ) -> list[ReferrerStats]:
        start = date.today() - timedelta(days=days - 1)
        q = (
            select(BlogPost.id)
            .where(BlogPost.project_id == self.project_id)
        )
        if practitioner_id is not None:
            q = q.where(BlogPost.practitioner_id == practitioner_id)
        r = await self.session.execute(q)
        post_ids = [row[0] for row in r.fetchall()]
        if not post_ids:
            return [
                ReferrerStats(source=s, count=0, percent=0.0)
                for s in ["telegram", "google", "facebook", "twitter", "direct", "other"]
            ]

        q_agg = (
            select(BlogAnalyticsDaily)
            .where(
                BlogAnalyticsDaily.project_id == self.project_id,
                BlogAnalyticsDaily.post_id.in_(post_ids),
                BlogAnalyticsDaily.date >= start,
            )
        )
        rows = (await self.session.execute(q_agg)).scalars().all()
        total = 0
        counts = {"telegram": 0, "facebook": 0, "twitter": 0, "google": 0, "direct": 0, "other": 0}
        for row in rows:
            counts["telegram"] += row.referrer_telegram
            counts["facebook"] += row.referrer_facebook
            counts["twitter"] += row.referrer_twitter
            counts["google"] += row.referrer_google
            counts["direct"] += row.referrer_direct
            counts["other"] += row.referrer_other
        total = sum(counts.values())
        if total == 0:
            return [
                ReferrerStats(source=s, count=0, percent=0.0)
                for s in ["telegram", "google", "facebook", "twitter", "direct", "other"]
            ]
        return [
            ReferrerStats(
                source=s,
                count=counts[s],
                percent=round((counts[s] / total) * 100, 2),
            )
            for s in ["telegram", "google", "facebook", "twitter", "direct", "other"]
        ]
