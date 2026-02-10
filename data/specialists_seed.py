"""
Seed 20+ тестових спеціалістів: цілителі, вчителі, художники, дизайнери.
Ціни: цілителі 500–1500₴, вчителі 300–800₴, дизайнери 1000–3000₴.
Портфоліо для художників/дизайнерів, блоги для цілителів.
Запуск: python -m data.specialists_seed (з кореня проєкту) або python data/specialists_seed.py
"""
from __future__ import annotations

import asyncio
import random
import logging
from pathlib import Path

# Додати корінь проєкту в path
ROOT = Path(__file__).resolve().parent.parent
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.connection import async_session_maker, engine
from app.models.base import Base
from app.models.specialist import Specialist
from app.models.specialist_content import SpecialistContent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ціни по нішах (грн/год): min, max
RATE_RANGES = {
    "healer": (500, 1500),
    "coach": (600, 1400),
    "teacher_math": (300, 800),
    "interior_designer": (1000, 3000),
    "3d_modeling": (800, 2500),
    "web_development": (900, 2800),
}

SPECIALISTS_DATA = [
    # Цілителі (блоги)
    {"name": "Олена Савченко", "service_type": "healer", "specialty": "Енергетичне цілительство, тривога"},
    {"name": "Михайло Коваль", "service_type": "healer", "specialty": "Робота з болем, остеохондроз"},
    {"name": "Наталія Бондаренко", "service_type": "healer", "specialty": "Панічні атаки, безсоння"},
    {"name": "Ірина Мельник", "service_type": "healer", "specialty": "Жіноче здоров'я, стрес"},
    {"name": "Андрій Шевченко", "service_type": "healer", "specialty": "Діти та батьки, заземлення"},
    {"name": "Тетяна Кравченко", "service_type": "healer", "specialty": "Хронічна втома, відновлення"},
    # Коучі
    {"name": "Юлія Гриценко", "service_type": "coach", "specialty": "Кар'єрний коучинг"},
    {"name": "Дмитро Лисенко", "service_type": "coach", "specialty": "Трансформаційний коучинг"},
    {"name": "Марина Ткаченко", "service_type": "coach", "specialty": "Лідерство та рішення"},
    {"name": "Олексій Петренко", "service_type": "coach", "specialty": "Життєві цілі та зміни"},
    # Вчителі математики
    {"name": "Світлана Олійник", "service_type": "teacher_math", "specialty": "Підготовка до ЗНО"},
    {"name": "Віктор Гончаренко", "service_type": "teacher_math", "specialty": "Алгебра 7–11 клас"},
    {"name": "Катерина Білик", "service_type": "teacher_math", "specialty": "Геометрія та олімпіади"},
    {"name": "Павло Рибак", "service_type": "teacher_math", "specialty": "Математика для дорослих"},
    # Дизайнери інтер'єру (портфоліо)
    {"name": "Анна Козак", "service_type": "interior_designer", "specialty": "Мінімалізм, скандинавський стиль"},
    {"name": "Євген Марченко", "service_type": "interior_designer", "specialty": "Лофт, комерційні простори"},
    {"name": "Оксана Семененко", "service_type": "interior_designer", "specialty": "Квартири та будинки"},
    {"name": "Ігор Денисенко", "service_type": "interior_designer", "specialty": "Офіси та ресторани"},
    # 3D / художники (портфоліо)
    {"name": "Артем Пономаренко", "service_type": "3d_modeling", "specialty": "3D візуалізація, архітектура"},
    {"name": "Марія Левченко", "service_type": "3d_modeling", "specialty": "Персонажі та ігрова графіка"},
    {"name": "Сергій Бондар", "service_type": "3d_modeling", "specialty": "Продуктова візуалізація"},
    {"name": "Яна Ковальчук", "service_type": "3d_modeling", "specialty": "Інтер'єрні рендери"},
    # Веб-розробка
    {"name": "Андрій Величко", "service_type": "web_development", "specialty": "Frontend, React"},
    {"name": "Назар Григорук", "service_type": "web_development", "specialty": "Backend, Python/FastAPI"},
    {"name": "Софія Тарасенко", "service_type": "web_development", "specialty": "Повний цикл, лендинги"},
]


def _rate(service_type: str) -> int:
    lo, hi = RATE_RANGES.get(service_type, (400, 1000))
    return random.randint(lo, hi)


async def ensure_tables() -> None:
    from app.models.user import User  # noqa: F401
    from app.models.conversation import Conversation  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tables ensured.")


async def seed_specialists_and_content() -> int:
    created = 0
    async with async_session_maker() as session:
        for s in SPECIALISTS_DATA:
            specialist = Specialist(
                name=s["name"],
                service_type=s["service_type"],
                delivery_method="human",
                specialty=s["specialty"],
                hourly_rate=_rate(s["service_type"]),
                bio=f"Спеціаліст: {s['specialty']}. Досвід роботи з клієнтами.",
                telegram_id=None,
                portfolio_url="https://example.com/portfolio" if s["service_type"] in ("interior_designer", "3d_modeling", "web_development") else None,
                is_active=True,
                is_verified=random.choice([True, False]),
            )
            session.add(specialist)
            await session.flush()
            created += 1

            # Блоги для цілителів
            if s["service_type"] == "healer":
                blog = SpecialistContent(
                    specialist_id=specialist.id,
                    content_type="blog",
                    title=f"Корисні поради: {s['specialty']}",
                    description=f"Як я працюю з темою {s['specialty'].lower()}. Досвід та рекомендації.",
                    media_urls=[],
                    target_audience=["clients_seeking_healing"],
                )
                session.add(blog)

            # Портфоліо для дизайнерів та 3D
            if s["service_type"] in ("interior_designer", "3d_modeling"):
                port = SpecialistContent(
                    specialist_id=specialist.id,
                    content_type="portfolio_item",
                    title=f"Робота: {s['specialty'][:30]}",
                    description="Приклад проєкту з мого портфоліо.",
                    media_urls=["https://example.com/img1.jpg"],
                    price=random.randint(5000, 50000) if s["service_type"] == "3d_modeling" else None,
                    is_for_sale=(s["service_type"] == "3d_modeling" and random.choice([True, False])),
                    target_audience=["design_lovers", "business"],
                )
                session.add(port)

        await session.commit()
    return created


async def main() -> None:
    await ensure_tables()
    n = await seed_specialists_and_content()
    print(f"✅ Specialists seed done: {n} specialists (+ blogs/portfolio).")


if __name__ == "__main__":
    asyncio.run(main())
