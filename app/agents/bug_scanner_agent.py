"""
Bug Scanner Agent — сканер відомих багів та проблем з даними.
- Перевіряє відомі баги з паспорту (B-02...B-09)
- Шукає порушення цілісності даних
- Знаходить сирітські записи (orphans)
- Виводить статус кожного багу
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import text

from app.agents.base_agent import BaseAgent
from app.database.connection import async_session_factory
from app.models.agent_config import AgentSeverity

logger = logging.getLogger(__name__)


class BugScannerAgent(BaseAgent):
    AGENT_NAME = "bug_scanner"
    AGENT_TYPE = "bug_scanner"
    DESCRIPTION = "Сканер відомих багів, цілісності даних та orphan записів"
    DEFAULT_INTERVAL = 600  # кожні 10 хвилин

    async def execute(self) -> dict:
        results = {
            "bugs_checked": [],
            "active_bugs": [],
            "data_issues": [],
            "fixed_since_last": [],
        }

        # B-02: Seed-акаунти без відомих паролів
        await self._check_seed_accounts(results)

        # B-04: Спеціалісти без геолокації
        await self._check_missing_coordinates(results)

        # B-06: Дублікати постів
        await self._check_duplicate_posts(results)

        # B-07: Порожні акаунти (без email)
        await self._check_empty_accounts(results)

        # B-09: Users без відповідних сторінок
        await self._check_role_page_mismatch(results)

        # Цілісність: Specialists без user_id
        await self._check_specialist_user_link(results)

        # Цілісність: PractitionerProfiles без specialist
        await self._check_orphan_profiles(results)

        # Цілісність: Букінги без спеціаліста
        await self._check_orphan_bookings(results)

        # Підсумок
        total_issues = len(results["active_bugs"]) + len(results["data_issues"])
        if total_issues > 0:
            await self.log(
                action="scan_complete",
                message=f"Found {total_issues} issue(s): {len(results['active_bugs'])} bugs, {len(results['data_issues'])} data issues",
                severity=AgentSeverity.WARNING if total_issues < 5 else AgentSeverity.ERROR,
                details={
                    "active_bugs": results["active_bugs"],
                    "data_issues": results["data_issues"],
                },
            )
        else:
            await self.log(
                action="scan_clean",
                message=f"No issues found. Checked: {len(results['bugs_checked'])} items",
                severity=AgentSeverity.INFO,
            )

        return results

    async def _check_seed_accounts(self, results: dict):
        """B-02: Seed-акаунти з невідомими паролями."""
        results["bugs_checked"].append("B-02")
        try:
            async with async_session_factory() as session:
                query = text(
                    "SELECT id, email, role FROM users "
                    "WHERE email LIKE '%@example.com' "
                    "ORDER BY id"
                )
                result = await session.execute(query)
                seeds = result.fetchall()
                if seeds:
                    results["active_bugs"].append({
                        "id": "B-02",
                        "description": "Seed accounts with unknown passwords",
                        "count": len(seeds),
                        "accounts": [{"id": s.id, "email": s.email} for s in seeds],
                    })
        except Exception as e:
            logger.warning(f"[{self.AGENT_NAME}] B-02 check failed: {e}")

    async def _check_missing_coordinates(self, results: dict):
        """B-04: Спеціалісти без lat/lng."""
        results["bugs_checked"].append("B-04")
        try:
            async with async_session_factory() as session:
                query = text(
                    "SELECT id, name FROM specialists "
                    "WHERE (latitude IS NULL OR longitude IS NULL) AND is_active = true"
                )
                result = await session.execute(query)
                no_coords = result.fetchall()
                if no_coords:
                    results["active_bugs"].append({
                        "id": "B-04",
                        "description": "Active specialists without coordinates",
                        "count": len(no_coords),
                        "specialists": [{"id": s.id, "name": s.name} for s in no_coords],
                    })
        except Exception as e:
            logger.warning(f"[{self.AGENT_NAME}] B-04 check failed: {e}")

    async def _check_duplicate_posts(self, results: dict):
        """B-06: Дублікати блог-постів."""
        results["bugs_checked"].append("B-06")
        try:
            async with async_session_factory() as session:
                query = text(
                    "SELECT title, practitioner_id, COUNT(*) as cnt "
                    "FROM blog_posts "
                    "GROUP BY title, practitioner_id "
                    "HAVING COUNT(*) > 1"
                )
                result = await session.execute(query)
                duplicates = result.fetchall()
                if duplicates:
                    results["active_bugs"].append({
                        "id": "B-06",
                        "description": "Duplicate blog posts",
                        "duplicates": [
                            {"title": d.title, "practitioner_id": d.practitioner_id, "count": d.cnt}
                            for d in duplicates
                        ],
                    })
        except Exception as e:
            logger.warning(f"[{self.AGENT_NAME}] B-06 check failed: {e}")

    async def _check_empty_accounts(self, results: dict):
        """B-07: Порожні акаунти."""
        results["bugs_checked"].append("B-07")
        try:
            async with async_session_factory() as session:
                query = text(
                    "SELECT id, username, email FROM users "
                    "WHERE (email IS NULL OR email = '') "
                    "AND (username IS NULL OR username = '')"
                )
                result = await session.execute(query)
                empty = result.fetchall()
                if empty:
                    results["active_bugs"].append({
                        "id": "B-07",
                        "description": "Empty accounts (no email, no username)",
                        "count": len(empty),
                        "user_ids": [u.id for u in empty],
                    })
        except Exception as e:
            logger.warning(f"[{self.AGENT_NAME}] B-07 check failed: {e}")

    async def _check_role_page_mismatch(self, results: dict):
        """B-09: Users з role=user без відповідної сторінки."""
        results["bugs_checked"].append("B-09")
        try:
            async with async_session_factory() as session:
                query = text(
                    "SELECT id, email, role FROM users "
                    "WHERE role = 'user' AND is_active = true"
                )
                result = await session.execute(query)
                users = result.fetchall()
                # Це інформаційна перевірка — role=user має мати сторінку
                if users:
                    results["data_issues"].append({
                        "id": "B-09",
                        "description": f"{len(users)} active user(s) with role=user (need user dashboard page)",
                        "count": len(users),
                    })
        except Exception as e:
            logger.warning(f"[{self.AGENT_NAME}] B-09 check failed: {e}")

    async def _check_specialist_user_link(self, results: dict):
        """Specialists без user_id (не прив'язані до акаунту)."""
        results["bugs_checked"].append("specialist_user_link")
        try:
            async with async_session_factory() as session:
                query = text(
                    "SELECT id, name FROM specialists "
                    "WHERE user_id IS NULL AND is_active = true"
                )
                result = await session.execute(query)
                unlinked = result.fetchall()
                if unlinked:
                    results["data_issues"].append({
                        "type": "unlinked_specialists",
                        "description": "Active specialists without user account link",
                        "count": len(unlinked),
                        "specialists": [{"id": s.id, "name": s.name} for s in unlinked],
                    })
        except Exception as e:
            logger.warning(f"[{self.AGENT_NAME}] Specialist link check failed: {e}")

    async def _check_orphan_profiles(self, results: dict):
        """PractitionerProfiles без відповідного specialist."""
        results["bugs_checked"].append("orphan_profiles")
        try:
            async with async_session_factory() as session:
                query = text(
                    "SELECT pp.id, pp.specialist_id FROM practitioner_profiles pp "
                    "LEFT JOIN specialists s ON pp.specialist_id = s.id "
                    "WHERE s.id IS NULL"
                )
                result = await session.execute(query)
                orphans = result.fetchall()
                if orphans:
                    results["data_issues"].append({
                        "type": "orphan_profiles",
                        "description": "PractitionerProfiles without matching specialist",
                        "count": len(orphans),
                        "profile_ids": [o.id for o in orphans],
                    })
        except Exception as e:
            logger.warning(f"[{self.AGENT_NAME}] Orphan profiles check failed: {e}")

    async def _check_orphan_bookings(self, results: dict):
        """Букінги без спеціаліста."""
        results["bugs_checked"].append("orphan_bookings")
        try:
            async with async_session_factory() as session:
                query = text(
                    "SELECT b.id FROM bookings b "
                    "LEFT JOIN specialists s ON b.specialist_id = s.id "
                    "WHERE s.id IS NULL"
                )
                result = await session.execute(query)
                orphans = result.fetchall()
                if orphans:
                    results["data_issues"].append({
                        "type": "orphan_bookings",
                        "description": "Bookings referencing non-existent specialists",
                        "count": len(orphans),
                    })
        except Exception as e:
            logger.warning(f"[{self.AGENT_NAME}] Orphan bookings check failed: {e}")


# Singleton
bug_scanner_agent = BugScannerAgent()
