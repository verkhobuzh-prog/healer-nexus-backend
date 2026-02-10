"""
Pre-seed learning: завантаження тренувальних розмов у KnowledgeBase та 20 спеціалістів.
load_initial_data() — створює спеціалістів (цілителі, вчителі, художники, дизайнери),
блоги для цілителів, портфоліо для художників/дизайнерів.
Запуск: python -m app.admin.pre_seed_learning або python -m data.run_seed
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
from pathlib import Path

from app.config import settings
from app.database.connection import async_session_maker, engine
from app.models.base import Base
from app.models.knowledge_base import KnowledgeBase
from app.models.specialist import Specialist
from app.models.specialist_content import SpecialistContent
from app.models.user import User  # noqa: F401
from app.models.conversation import Conversation  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PRE_SEED_PATH = BASE_DIR / "data" / "healers_pre_seed.json"

# 20 спеціалістів: цілителі 500–1500₴, вчителі 300–800₴, художники 800–2000₴, дизайнери 1000–3000₴
SPECIALISTS_SPEC = [
    # Цілителі (медитація, рейкі, йога) — 500–1500₴
    {"name": "Олена", "service_type": "healer", "service_types": ["healer", "meditation"], "specialty": "Медитація та релаксація", "rate_min": 500, "rate_max": 1500},
    {"name": "Тарас", "service_type": "healer", "service_types": ["healer", "reiki"], "specialty": "Рейкі, енергетичне цілительство", "rate_min": 500, "rate_max": 1500},
    {"name": "Марія", "service_type": "healer", "service_types": ["healer", "yoga"], "specialty": "Йога та дихання", "rate_min": 500, "rate_max": 1500},
    {"name": "Наталія", "service_type": "healer", "service_types": ["healer", "coach"], "specialty": "Енергетичний баланс", "rate_min": 600, "rate_max": 1400},
    {"name": "Василь", "service_type": "healer", "service_types": ["healer"], "specialty": "Масаж, релакс", "rate_min": 500, "rate_max": 1500},
    {"name": "Ірина", "service_type": "healer", "service_types": ["healer", "meditation"], "specialty": "Тривога та безсоння", "rate_min": 600, "rate_max": 1400},
    # Вчителі (математика, українська, англійська) — 300–800₴
    {"name": "Анна", "service_type": "teacher_math", "service_types": ["teacher_math"], "specialty": "Математика, підготовка до ЗНО", "rate_min": 300, "rate_max": 800},
    {"name": "Іван", "service_type": "teacher_math", "service_types": ["teacher_math", "teacher_ukrainian"], "specialty": "Українська мова та література", "rate_min": 300, "rate_max": 800},
    {"name": "Софія", "service_type": "teacher_math", "service_types": ["teacher_english"], "specialty": "Англійська мова", "rate_min": 350, "rate_max": 800},
    {"name": "Олександр", "service_type": "teacher_math", "service_types": ["teacher_math"], "specialty": "Алгебра та геометрія", "rate_min": 300, "rate_max": 700},
    {"name": "Марія К.", "service_type": "teacher_math", "service_types": ["teacher_english"], "specialty": "Англійська для дорослих", "rate_min": 400, "rate_max": 800},
    {"name": "Дмитро", "service_type": "teacher_math", "service_types": ["teacher_math"], "specialty": "Математика 7–11 клас", "rate_min": 300, "rate_max": 750},
    # Художники (живопис, графіка) — 800–2000₴
    {"name": "Андрій", "service_type": "3d_modeling", "service_types": ["artist", "painting"], "specialty": "Живопис, олійні техніки", "rate_min": 800, "rate_max": 2000},
    {"name": "Катерина", "service_type": "3d_modeling", "service_types": ["artist", "graphics"], "specialty": "Графіка та ілюстрація", "rate_min": 800, "rate_max": 2000},
    {"name": "Михайло", "service_type": "3d_modeling", "service_types": ["artist", "painting"], "specialty": "Акварель, портрет", "rate_min": 900, "rate_max": 1800},
    {"name": "Оксана", "service_type": "3d_modeling", "service_types": ["artist", "graphics"], "specialty": "Цифрова ілюстрація", "rate_min": 800, "rate_max": 2000},
    # Дизайнери (інтер'єр, меблі, 3D) — 1000–3000₴
    {"name": "Денис", "service_type": "interior_designer", "service_types": ["interior_designer"], "specialty": "Інтер'єр житлових та комерційних приміщень", "rate_min": 1000, "rate_max": 3000},
    {"name": "Юлія", "service_type": "interior_designer", "service_types": ["interior_designer", "3d_modeling"], "specialty": "Меблі та 3D візуалізація", "rate_min": 1000, "rate_max": 3000},
    {"name": "Ігор", "service_type": "interior_designer", "service_types": ["3d_modeling", "interior_designer"], "specialty": "3D візуалізація інтер'єру", "rate_min": 1200, "rate_max": 2800},
    {"name": "Анна Д.", "service_type": "interior_designer", "service_types": ["interior_designer"], "specialty": "Інтер'єр квартир та будинків", "rate_min": 1000, "rate_max": 3000},
]


async def ensure_tables() -> None:
    """Створити таблиці, якщо немає (включно knowledge_base)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tables ensured.")


async def load_initial_data(progress_callback=None) -> dict[str, int]:
    """
    Створити 20 спеціалістів з реалістичними українськими даними,
    блоги для цілителів, портфоліо для художників/дизайнерів.
    progress_callback(i, total, name) — опційно викликається після кожного спеціаліста.
    Повертає {"specialists": N, "blogs": N, "portfolio_items": N}.
    """
    await ensure_tables()
    specialists_created = 0
    blogs_created = 0
    portfolio_created = 0
    total = len(SPECIALISTS_SPEC)

    try:
        async with async_session_maker() as session:
            for i, spec in enumerate(SPECIALISTS_SPEC, 1):
                try:
                    rate = random.randint(spec["rate_min"], spec["rate_max"])
                    specialist = Specialist(
                        name=spec["name"],
                        service_type=spec["service_type"],
                        service_types=spec.get("service_types"),
                        delivery_method="human",
                        specialty=spec["specialty"],
                        hourly_rate=rate,
                        bio=f"Спеціаліст: {spec['specialty']}. Працюю з клієнтами.",
                        portfolio_url="https://example.com/portfolio" if spec["service_type"] in ("interior_designer", "3d_modeling") else None,
                        is_active=True,
                        is_verified=random.choice([True, False]),
                    )
                    session.add(specialist)
                    await session.flush()
                    specialists_created += 1
                    logger.info("Створено спеціаліста %s/%s: %s", i, total, spec["name"])
                    if progress_callback:
                        progress_callback(i, total, spec["name"])

                    if spec["service_type"] == "healer":
                        blog = SpecialistContent(
                            specialist_id=specialist.id,
                            content_type="blog",
                            title=f"Блог: {spec['specialty']}",
                            description=f"Корисні поради та досвід у сфері {spec['specialty'].lower()}.",
                            media_urls=[],
                            target_audience=["clients_seeking_healing"],
                        )
                        session.add(blog)
                        blogs_created += 1

                    if spec["service_type"] in ("interior_designer", "3d_modeling"):
                        port = SpecialistContent(
                            specialist_id=specialist.id,
                            content_type="portfolio_item",
                            title=f"Портфоліо: {spec['specialty'][:40]}",
                            description="Приклад робіт.",
                            media_urls=["https://example.com/portfolio/1.jpg"],
                            price=random.randint(3000, 25000) if random.choice([True, False]) else None,
                            is_for_sale=random.choice([True, False]),
                            target_audience=["design_lovers", "business"],
                        )
                        session.add(port)
                        portfolio_created += 1

                except Exception as e:
                    logger.exception("Помилка створення спеціаліста %s: %s", spec.get("name"), e)
                    await session.rollback()
                    raise

            await session.commit()
    except Exception as e:
        logger.exception("load_initial_data помилка: %s", e)
        raise

    return {"specialists": specialists_created, "blogs": blogs_created, "portfolio_items": portfolio_created}


async def load_training_into_knowledge_base() -> int:
    """Завантажити data/healers_pre_seed.json у таблицю knowledge_base. Повертає кількість записів."""
    if not PRE_SEED_PATH.exists():
        logger.warning("File not found: %s", PRE_SEED_PATH)
        return 0

    with open(PRE_SEED_PATH, "r", encoding="utf-8") as f:
        items = json.load(f)

    if not items:
        logger.info("No items in %s", PRE_SEED_PATH)
        return 0

    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    count = 0

    async with async_session_maker() as session:
        for item in items:
            service_type = item.get("service_type", "healer")
            messages = item.get("messages", [])
            data = {
                "messages": messages,
                "converted": item.get("converted", False),
                "pain_points": item.get("pain_points", []),
            }
            entry = KnowledgeBase(
                project_id=project_id,
                entry_type="conversation",
                service_type=service_type,
                data=data,
                message_count=len(messages),
            )
            session.add(entry)
            count += 1
        await session.commit()

    logger.info("Loaded %s training entries into knowledge_base.", count)
    return count


async def main() -> None:
    """За замовчуванням: тільки KnowledgeBase з healers_pre_seed.json."""
    await ensure_tables()
    n = await load_training_into_knowledge_base()
    print(f"✅ Pre-seed learning (KnowledgeBase): {n} записів з {PRE_SEED_PATH.name}")


if __name__ == "__main__":
    asyncio.run(main())
