"""
Booking CRUD and specialist notification. Multi-tenant by project_id.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingStatus
from app.models.specialist import Specialist
from app.models.practitioner_profile import PractitionerProfile
from app.services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)


def _get_telegram_bot():
    from telegram import Bot
    from app.config import settings
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not configured")
    return Bot(token=token)


class BookingService:
    def __init__(self, session: AsyncSession, project_id: str):
        self.session = session
        self.project_id = project_id

    async def create_booking(
        self,
        user_id: int,
        specialist_id: int,
        reason: Optional[str] = None,
        user_message: Optional[str] = None,
        conversation_id: Optional[int] = None,
        practitioner_id: Optional[int] = None,
        contact_method: str = "telegram",
        scheduled_at: Optional[datetime] = None,
    ) -> Booking:
        specialist = await self._get_specialist(specialist_id)
        if not specialist:
            raise ValueError("Specialist not found or inactive")
        practitioner_id = practitioner_id or await self._get_practitioner_id(specialist_id)
        booking = Booking(
            project_id=self.project_id,
            user_id=user_id,
            specialist_id=specialist_id,
            practitioner_id=practitioner_id,
            conversation_id=conversation_id,
            status=BookingStatus.PENDING.value,
            reason=reason,
            user_message=user_message,
            contact_method=contact_method,
            scheduled_at=scheduled_at,
        )
        self.session.add(booking)
        await self.session.flush()
        try:
            await self.notify_specialist_telegram(booking)
        except Exception as e:
            logger.exception("Booking Telegram notification failed: %s", e)
        try:
            rec_svc = RecommendationService(self.session, self.project_id)
            await rec_svc.record_booked(
                specialist_id=specialist_id,
                user_id=user_id,
                booking_id=booking.id,
            )
        except Exception as e:
            logger.exception("Recommendation record_booked failed: %s", e)
        await self.session.commit()
        await self.session.refresh(booking)
        return booking

    async def _get_specialist(self, specialist_id: int):
        r = await self.session.execute(
            select(Specialist).where(
                Specialist.id == specialist_id,
                Specialist.is_active == True,
            )
        )
        return r.scalar_one_or_none()

    async def _get_practitioner_id(self, specialist_id: int) -> Optional[int]:
        r = await self.session.execute(
            select(PractitionerProfile.id).where(
                PractitionerProfile.specialist_id == specialist_id,
                PractitionerProfile.project_id == self.project_id,
                PractitionerProfile.is_active == True,
            ).limit(1)
        )
        return r.scalar_one_or_none()

    async def get_booking(self, booking_id: int) -> Optional[Booking]:
        r = await self.session.execute(
            select(Booking).where(
                Booking.id == booking_id,
                Booking.project_id == self.project_id,
            )
        )
        return r.scalar_one_or_none()

    async def list_bookings(
        self,
        user_id: Optional[int] = None,
        specialist_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Booking], int]:
        q = select(Booking).where(Booking.project_id == self.project_id)
        count_q = select(func.count(Booking.id)).where(Booking.project_id == self.project_id)
        if user_id is not None:
            q = q.where(Booking.user_id == user_id)
            count_q = count_q.where(Booking.user_id == user_id)
        if specialist_id is not None:
            q = q.where(Booking.specialist_id == specialist_id)
            count_q = count_q.where(Booking.specialist_id == specialist_id)
        if status is not None:
            q = q.where(Booking.status == status)
            count_q = count_q.where(Booking.status == status)
        total = (await self.session.execute(count_q)).scalar() or 0
        q = q.order_by(Booking.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        r = await self.session.execute(q)
        return list(r.scalars().all()), total

    async def confirm_booking(
        self, booking_id: int, specialist_notes: Optional[str] = None
    ) -> Optional[Booking]:
        booking = await self.get_booking(booking_id)
        if not booking or booking.status != BookingStatus.PENDING.value:
            return None
        booking.status = BookingStatus.CONFIRMED.value
        booking.confirmed_at = datetime.now(timezone.utc)
        if specialist_notes is not None:
            booking.specialist_notes = specialist_notes
        await self.session.commit()
        await self.session.refresh(booking)
        return booking

    async def cancel_booking(
        self, booking_id: int, cancel_reason: Optional[str] = None
    ) -> Optional[Booking]:
        booking = await self.get_booking(booking_id)
        if not booking or booking.status not in (
            BookingStatus.PENDING.value,
            BookingStatus.CONFIRMED.value,
        ):
            return None
        booking.status = BookingStatus.CANCELLED.value
        booking.cancelled_at = datetime.now(timezone.utc)
        if cancel_reason is not None:
            booking.cancel_reason = cancel_reason
        await self.session.commit()
        await self.session.refresh(booking)
        return booking

    async def complete_booking(self, booking_id: int) -> Optional[Booking]:
        booking = await self.get_booking(booking_id)
        if not booking or booking.status != BookingStatus.CONFIRMED.value:
            return None
        booking.status = BookingStatus.COMPLETED.value
        await self.session.commit()
        await self.session.refresh(booking)
        return booking

    async def notify_specialist_telegram(self, booking: Booking) -> bool:
        """Send booking notification to specialist. Sets telegram_notified on success."""
        specialist_r = await self.session.execute(
            select(Specialist).where(Specialist.id == booking.specialist_id)
        )
        specialist = specialist_r.scalar_one_or_none()
        if not specialist:
            return False
        profile_r = await self.session.execute(
            select(PractitionerProfile).where(
                PractitionerProfile.specialist_id == booking.specialist_id,
                PractitionerProfile.project_id == self.project_id,
            ).limit(1)
        )
        profile = profile_r.scalar_one_or_none()
        chat_id = None
        if getattr(profile, "telegram_channel_id", None) and str(profile.telegram_channel_id).strip():
            chat_id = str(profile.telegram_channel_id).strip()
        if not chat_id and getattr(profile, "contact_link", None):
            link = (profile.contact_link or "").strip()
            if link.startswith("t.me/") or "t.me/" in link:
                chat_id = "@" + link.split("t.me/")[-1].split("/")[0].split("?")[0]
        if not chat_id and specialist.telegram_id:
            chat_id = int(specialist.telegram_id)
        if not chat_id:
            logger.warning("No Telegram contact for specialist_id=%s", booking.specialist_id)
            return False
        reason_raw = (booking.reason or booking.user_message or "—")[:200]
        reason = reason_raw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        text = (
            "📋 <b>Новий запис!</b>\n\n"
            "Клієнт хоче записатись до вас.\n"
            f"Причина: {reason}\n"
            f"Контакт: {booking.contact_method}\n\n"
            "Запишіть або зв'яжіться з клієнтом."
        )
        try:
            bot = _get_telegram_bot()
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
            )
            booking.telegram_notified = True
            await self.session.flush()
            return True
        except Exception as e:
            logger.error("Telegram send to %s failed: %s", chat_id, e)
            return False
