"""
Executes tool calls from Gemini responses.
Bridges between Gemini function calling and actual services.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.specialist import Specialist
from app.models.practitioner_profile import PractitionerProfile
from app.services.specialist_matcher import SpecialistMatcher
from app.services.booking_service import BookingService


class ChatToolExecutor:
    def __init__(
        self,
        session: AsyncSession,
        project_id: str,
        user_id: int,
        conversation_id: int | None = None,
    ):
        self.session = session
        self.project_id = project_id
        self.user_id = user_id
        self.conversation_id = conversation_id

    async def execute_tool_call(self, function_name: str, arguments: dict) -> dict:
        """Execute a tool call and return the result as a dict for Gemini."""
        args = arguments or {}
        if function_name == "search_specialists":
            return await self._search_specialists(
                query=args.get("query", ""),
                specialty=args.get("specialty"),
            )
        if function_name == "create_booking":
            return await self._create_booking(
                specialist_id=int(args.get("specialist_id", 0)),
                reason=args.get("reason") or "",
            )
        if function_name == "get_specialist_details":
            return await self._get_specialist_details(
                specialist_id=int(args.get("specialist_id", 0)),
            )
        return {"error": f"Unknown function: {function_name}"}

    async def _search_specialists(
        self, query: str, specialty: str | None = None
    ) -> dict:
        matcher = SpecialistMatcher(self.session, self.project_id)
        results = await matcher.search(query=query, specialty=specialty, limit=5)
        if not results:
            return {
                "specialists": [],
                "message": "Не знайдено спеціалістів за цим запитом",
            }
        return {
            "specialists": results,
            "message": f"Знайдено {len(results)} спеціалістів",
        }

    async def _create_booking(self, specialist_id: int, reason: str) -> dict:
        svc = BookingService(self.session, self.project_id)
        try:
            booking = await svc.create_booking(
                user_id=self.user_id,
                specialist_id=specialist_id,
                reason=reason or None,
                conversation_id=self.conversation_id,
                contact_method="telegram",
            )
            return {
                "success": True,
                "booking_id": booking.id,
                "status": booking.status,
                "message": "Запис створено! Спеціаліст отримає повідомлення.",
            }
        except ValueError as e:
            return {"success": False, "error": str(e)}

    async def _get_specialist_details(self, specialist_id: int) -> dict:
        r = await self.session.execute(
            select(Specialist).where(
                Specialist.id == specialist_id,
                Specialist.is_active == True,
            )
        )
        spec = r.scalar_one_or_none()
        if not spec:
            return {"error": "Спеціаліст не знайдений", "specialist_id": specialist_id}
        profile_r = await self.session.execute(
            select(PractitionerProfile).where(
                PractitionerProfile.specialist_id == specialist_id,
                PractitionerProfile.project_id == self.project_id,
            ).limit(1)
        )
        profile = profile_r.scalar_one_or_none()
        contact = getattr(profile, "contact_link", None) if profile else None
        if not contact and spec.portfolio_url and "t.me" in (spec.portfolio_url or ""):
            contact = spec.portfolio_url
        return {
            "id": spec.id,
            "name": spec.name,
            "specialty": spec.specialty or "",
            "description": spec.bio or "",
            "unique_story": getattr(profile, "unique_story", None) or "",
            "contact_link": contact,
            "hourly_rate": spec.hourly_rate,
            "delivery_method": spec.delivery_method,
        }
