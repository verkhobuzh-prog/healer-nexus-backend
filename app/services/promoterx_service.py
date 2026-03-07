"""
PromoterX: daily report aggregation and Telegram delivery.
Uses existing Booking, BlogAnalytics, Recommendation data and BlogTelegram/telegram to send.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone, timedelta

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.specialist import Specialist
from app.models.blog_analytics_daily import BlogAnalyticsDaily
from app.models.blog_post import BlogPost
from app.models.specialist_recommendation import SpecialistRecommendation
from app.config import settings

logger = logging.getLogger(__name__)


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _today_start_utc() -> datetime:
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


class PromoterXService:
    """Aggregates daily metrics and sends report to admin Telegram."""

    @staticmethod
    async def generate_daily_report(db: AsyncSession, project_id: str) -> str:
        today = _today_utc()
        today_start = _today_start_utc()
        tomorrow_start = today_start + timedelta(days=1)

        # 1) Bookings today + top 3 niches
        q_bookings_today = (
            select(func.count(Booking.id))
            .where(
                Booking.project_id == project_id,
                Booking.created_at >= today_start,
                Booking.created_at < tomorrow_start,
            )
        )
        total_bookings = (await db.execute(q_bookings_today)).scalar() or 0

        q_top_niches = (
            select(Specialist.service_type, func.count(Booking.id).label("cnt"))
            .select_from(Booking)
            .join(Specialist, Booking.specialist_id == Specialist.id)
            .where(
                Booking.project_id == project_id,
                Booking.created_at >= today_start,
                Booking.created_at < tomorrow_start,
            )
            .group_by(Specialist.service_type)
            .order_by(func.count(Booking.id).desc())
            .limit(3)
        )
        r_niches = await db.execute(q_top_niches)
        top_niches = [row[0] for row in r_niches.fetchall()]
        niches_line = ", ".join(top_niches) if top_niches else "—"

        # 2) Blog views today + top 3 posts
        q_views_today = (
            select(func.coalesce(func.sum(BlogAnalyticsDaily.views_total), 0))
            .where(
                BlogAnalyticsDaily.project_id == project_id,
                BlogAnalyticsDaily.date == today,
            )
        )
        total_views = int((await db.execute(q_views_today)).scalar() or 0)

        q_top_posts = (
            select(BlogAnalyticsDaily.post_id, func.sum(BlogAnalyticsDaily.views_total).label("v"))
            .where(
                BlogAnalyticsDaily.project_id == project_id,
                BlogAnalyticsDaily.date == today,
            )
            .group_by(BlogAnalyticsDaily.post_id)
            .order_by(func.sum(BlogAnalyticsDaily.views_total).desc())
            .limit(3)
        )
        r_posts = await db.execute(q_top_posts)
        post_ids = [row[0] for row in r_posts.fetchall()]
        top_titles: list[str] = []
        if post_ids:
            q_titles = select(BlogPost.id, BlogPost.title).where(
                BlogPost.id.in_(post_ids),
                BlogPost.project_id == project_id,
            )
            r_t = await db.execute(q_titles)
            id_to_title = {row[0]: (row[1] or "—") for row in r_t.fetchall()}
            top_titles = [id_to_title.get(pid, "—")[:50] for pid in post_ids]
        top_post_line = top_titles[0] if top_titles else "—"

        # 3) Recommendation conversion today
        q_rec_today = (
            select(
                func.count(SpecialistRecommendation.id).label("total"),
                func.sum(case((SpecialistRecommendation.booked == True, 1), else_=0)).label("booked"),
            )
            .where(
                SpecialistRecommendation.project_id == project_id,
                SpecialistRecommendation.recommended_at >= today_start,
                SpecialistRecommendation.recommended_at < tomorrow_start,
            )
        )
        r_rec = await db.execute(q_rec_today)
        row_rec = r_rec.one()
        rec_total = int(row_rec.total or 0)
        rec_booked = int(row_rec.booked or 0)
        conversion_pct = round((rec_booked / rec_total * 100), 1) if rec_total else 0

        # 4) Format report
        date_str = today.strftime("%Y-%m-%d")
        report = (
            "───────────────────────\n"
            "📊 Healer Nexus — Daily Report\n"
            f"📅 {date_str}\n\n"
            f"👥 Бронювання сьогодні: {total_bookings}\n"
            f"🏆 Топ ніші: {niches_line}\n\n"
            f"📝 Перегляди блогу: {total_views}\n"
            f"🔥 Топ пост: {top_post_line}\n\n"
            f"🎯 Конверсія: {conversion_pct}%\n"
            "───────────────────────"
        )

        # 5) Send to admin via Telegram
        admin_chat_id = getattr(settings, "ADMIN_CHAT_ID", "").strip()
        if not admin_chat_id:
            logger.warning("PromoterX: ADMIN_CHAT_ID not set, report not sent")
            return report
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            logger.warning("PromoterX: TELEGRAM_BOT_TOKEN not set, report not sent")
            return report
        try:
            from telegram import Bot
            bot = Bot(token=token)
            await bot.send_message(chat_id=admin_chat_id, text=report, parse_mode="HTML")
            logger.info("PromoterX: daily report sent to %s", admin_chat_id)
        except Exception as e:
            logger.exception("PromoterX: failed to send report: %s", e)
        return report
