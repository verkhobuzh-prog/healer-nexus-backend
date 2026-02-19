"""
Searches and ranks specialists based on user query/symptoms.
Used by AI chat to find relevant specialists.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.specialist import Specialist
from app.models.practitioner_profile import PractitionerProfile


class SpecialistMatcher:
    def __init__(self, session: AsyncSession, project_id: str):
        self.session = session
        self.project_id = project_id

    async def search(
        self,
        query: str,
        specialty: str | None = None,
        limit: int = 5,
    ) -> list[dict]:
        """
        Search specialists by query keywords.
        Matches against: name, specialty, bio (description), practitioner's unique_story.
        Returns list of dicts with specialist info + match_reason.
        """
        if not query or not query.strip():
            return []
        keywords = [k.strip().lower() for k in query.strip().split() if k.strip()]
        if not keywords:
            return []

        # Load active specialists; left join practitioner profile for this project
        q = (
            select(Specialist, PractitionerProfile)
            .select_from(Specialist)
            .outerjoin(
                PractitionerProfile,
                (PractitionerProfile.specialist_id == Specialist.id)
                & (PractitionerProfile.project_id == self.project_id)
                & (PractitionerProfile.is_active == True),
            )
            .where(Specialist.is_active == True)
        )
        if specialty and specialty.strip():
            q = q.where(
                or_(
                    Specialist.specialty.ilike(f"%{specialty.strip()}%"),
                    Specialist.service_type.ilike(f"%{specialty.strip()}%"),
                )
            )
        result = await self.session.execute(q)
        rows = result.unique().all()
        specialists_with_profile = [(row[0], row[1]) for row in rows]

        scored = []
        for spec, profile in specialists_with_profile:
            searchable = " ".join(
                filter(
                    None,
                    [
                        (spec.name or ""),
                        (spec.specialty or ""),
                        (spec.bio or ""),
                        (getattr(profile, "unique_story", None) or "") if profile else "",
                    ],
                )
            ).lower()
            score = 0
            match_reasons = []
            for kw in keywords:
                if kw in searchable:
                    score += 1
                    if (spec.specialty or "").lower().find(kw) >= 0:
                        score += 2
                        if "specialty" not in str(match_reasons):
                            match_reasons.append(f"Спеціалізується на: {spec.specialty}")
                    elif (spec.bio or "").lower().find(kw) >= 0:
                        score += 1
                        match_reasons.append(f"Працює з: {kw}")
            if specialty and specialty.strip():
                if (spec.specialty or "").lower().find(specialty.strip().lower()) >= 0:
                    score += 3
            if score == 0 and not specialty:
                continue
            contact_link = getattr(profile, "contact_link", None) if profile else None
            if not contact_link and spec.portfolio_url and "t.me" in (spec.portfolio_url or ""):
                contact_link = spec.portfolio_url
            match_reason = match_reasons[0] if match_reasons else f"Спеціалізація: {spec.specialty or '—'}"
            scored.append(
                {
                    "id": spec.id,
                    "name": spec.name,
                    "specialty": spec.specialty or "",
                    "description": spec.bio,
                    "rating": None,
                    "contact_link": contact_link,
                    "avatar_url": None,
                    "match_reason": match_reason,
                    "hourly_rate": getattr(spec, "hourly_rate", 0),
                    "delivery_method": getattr(spec, "delivery_method", "human"),
                    "_score": score,
                }
            )
        scored.sort(key=lambda x: (x["_score"], x["name"]), reverse=True)
        for s in scored:
            del s["_score"]
        return scored[:limit]

    async def get_specialist_context_for_ai(self, specialist_ids: list[int]) -> str:
        """Build a text summary of specialists for Gemini context."""
        if not specialist_ids:
            return ""
        result = await self.session.execute(
            select(Specialist).where(
                Specialist.id.in_(specialist_ids),
                Specialist.is_active == True,
            )
        )
        specialists = list(result.scalars().all())
        profile_result = await self.session.execute(
            select(PractitionerProfile).where(
                PractitionerProfile.specialist_id.in_(specialist_ids),
                PractitionerProfile.project_id == self.project_id,
            )
        )
        profiles = {p.specialist_id: p for p in profile_result.scalars().all()}
        lines = []
        for i, spec in enumerate(specialists, 1):
            profile = profiles.get(spec.id)
            contact = getattr(profile, "contact_link", None) if profile else None
            if not contact and spec.portfolio_url and "t.me" in (spec.portfolio_url or ""):
                contact = spec.portfolio_url
            contact_str = f", контакт: {contact}" if contact else ""
            lines.append(f"{i}. {spec.name} — {spec.specialty or '—'}{contact_str}")
        return "\n".join(lines) if lines else ""
