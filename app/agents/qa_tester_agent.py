"""
QA Tester Agent — автоматичне smoke-тестування API endpoints.
- Тестує критичні flow: health, specialists list, blog public
- Перевіряє час відповіді кожного endpoint
- Логує які endpoint працюють, які ні
"""
from __future__ import annotations

import logging
import time

import httpx

from app.agents.base_agent import BaseAgent
from app.models.agent_config import AgentSeverity

logger = logging.getLogger(__name__)


class QATesterAgent(BaseAgent):
    AGENT_NAME = "qa_tester"
    AGENT_TYPE = "qa_tester"
    DESCRIPTION = "Smoke-тестування критичних API endpoints"
    DEFAULT_INTERVAL = 900  # кожні 15 хвилин

    # Endpoints для тестування (GET, без авторизації)
    PUBLIC_ENDPOINTS = [
        {"path": "/api/health", "expected_status": 200, "name": "Health"},
        {"path": "/api/specialists", "expected_status": 200, "name": "Specialists List"},
        {"path": "/api/blog/posts/public", "expected_status": 200, "name": "Blog Public"},
        {"path": "/", "expected_status": 200, "name": "Landing Page"},
        {"path": "/login", "expected_status": 200, "name": "Login Page"},
    ]

    # Endpoints що потребують auth (тестуємо 401 без токену)
    AUTH_ENDPOINTS = [
        {"path": "/api/auth/me", "expected_status": 401, "name": "Auth Me (no token)"},
        {"path": "/api/admin/users", "expected_status": 401, "name": "Admin Users (no token)"},
    ]

    async def execute(self) -> dict:
        from app.config import settings
        base_url = getattr(settings, "BASE_URL", "http://localhost:8000")

        results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "endpoint_results": [],
        }

        all_endpoints = self.PUBLIC_ENDPOINTS + self.AUTH_ENDPOINTS

        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            for ep in all_endpoints:
                results["total_tests"] += 1
                test_result = await self._test_endpoint(
                    client, base_url, ep["path"], ep["expected_status"], ep["name"]
                )
                results["endpoint_results"].append(test_result)

                if test_result["status"] == "pass":
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(test_result)

        # Логування результатів
        if results["failed"] > 0:
            await self.log(
                action="qa_tests_failed",
                message=f"QA: {results['failed']}/{results['total_tests']} tests FAILED",
                severity=AgentSeverity.ERROR if results["failed"] > 2 else AgentSeverity.WARNING,
                details={
                    "failed_endpoints": [e["name"] for e in results["errors"]],
                    "results": results["endpoint_results"],
                },
            )
        else:
            await self.log(
                action="qa_tests_passed",
                message=f"QA: All {results['total_tests']} tests PASSED",
                severity=AgentSeverity.INFO,
                details={
                    "avg_response_ms": sum(
                        r.get("response_ms", 0) for r in results["endpoint_results"]
                    ) // max(len(results["endpoint_results"]), 1),
                },
            )

        return results

    async def _test_endpoint(
        self, client: httpx.AsyncClient, base_url: str,
        path: str, expected_status: int, name: str
    ) -> dict:
        """Тестує один endpoint."""
        try:
            start = time.time()
            resp = await client.get(f"{base_url}{path}")
            response_ms = int((time.time() - start) * 1000)

            passed = resp.status_code == expected_status

            result = {
                "name": name,
                "path": path,
                "expected": expected_status,
                "actual": resp.status_code,
                "response_ms": response_ms,
                "status": "pass" if passed else "fail",
            }

            if not passed:
                result["error"] = f"Expected {expected_status}, got {resp.status_code}"

            return result

        except httpx.ConnectError:
            return {
                "name": name,
                "path": path,
                "expected": expected_status,
                "actual": None,
                "response_ms": None,
                "status": "fail",
                "error": "Connection refused",
            }
        except httpx.ReadTimeout:
            return {
                "name": name,
                "path": path,
                "expected": expected_status,
                "actual": None,
                "response_ms": 15000,
                "status": "fail",
                "error": "Request timeout (15s)",
            }
        except Exception as e:
            return {
                "name": name,
                "path": path,
                "expected": expected_status,
                "actual": None,
                "response_ms": None,
                "status": "fail",
                "error": str(e),
            }


# Singleton
qa_tester_agent = QATesterAgent()
