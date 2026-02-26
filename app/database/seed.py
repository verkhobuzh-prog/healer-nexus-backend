"""
Автозаповнення бази при старті.
Перевіряє чи таблиця specialists порожня → якщо так, створює базових спеціалістів.
"""

import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import async_session_maker
from app.models.user import User
from app.models.specialist import Specialist
from app.models.practitioner_profile import PractitionerProfile
from app.core.security import hash_password  # ВИПРАВЛЕНО

logger = logging.getLogger(__name__)

SEED_SPECIALISTS = [
    {
        "user": {
            "email": "kozuballarisa@gmail.com",
            "username": "larisa_kozubal",
            "password": "Larisa2026!",
            "role": "practitioner",
        },
        "specialist": {
            "name": "Лариса Козубаль",
            "specialty": "Вчитель математики",
            "service_type": "teacher_math",
            "service_types": ["математика", "підготовка до ЗНО", "олімпіади"],
            "hourly_rate": 500,
            "bio": "Досвідчений вчитель математики з 20+ роками стажу. Підготовка до ЗНО, олімпіад, індивідуальні заняття.",
            "is_verified": True,
            "is_active": True,
            "delivery_method": "human",
        },
        "profile": {
            "slug": "larisa-kozubal",
            "empathy_ratio": 0.8,
            "style": "warm",
            "unique_story": "Я вірю, що кожна дитина здатна зрозуміти математику, якщо знайти правильний підхід.",
            "social_links": {"telegram": "https://t.me/larisa_math"},
        },
    },
    {
        "user": {
            "email": "olena.meditation@example.com",
            "username": "olena_meditation",
            "password": "Olena2026!",
            "role": "practitioner",
        },
        "specialist": {
            "name": "Олена Світлодарська",
            "specialty": "Медитація та mindfulness",
            "service_type": "healer",
            "service_types": ["медитація", "mindfulness", "дихальні практики", "релаксація"],
            "hourly_rate": 600,
            "bio": "Сертифікований інструктор з медитації. Допомагаю знайти внутрішній спокій та баланс через практики усвідомленості.",
            "is_verified": True,
            "is_active": True,
            "delivery_method": "human",
        },
        "profile": {
            "slug": "olena-meditation",
            "empathy_ratio": 0.9,
            "style": "gentle",
            "unique_story": "Медитація змінила моє життя 10 років тому, і тепер я допомагаю іншим знайти цей шлях.",
            "social_links": {"instagram": "https://instagram.com/olena_meditation"},
        },
    },
    {
        "user": {
            "email": "mykhailo.design@example.com",
            "username": "mykhailo_design",
            "password": "Mykhailo2026!",
            "role": "practitioner",
        },
        "specialist": {
            "name": "Михайло Крафтенко",
            "specialty": "UI/UX Дизайнер",
            "service_type": "interior_designer",
            "service_types": ["UI дизайн", "UX дослідження", "прототипування", "брендинг"],
            "hourly_rate": 800,
            "bio": "UI/UX дизайнер з досвідом у продуктових компаніях. Створюю інтерфейси, які люди люблять використовувати.",
            "is_verified": True,
            "is_active": True,
            "delivery_method": "human",
        },
        "profile": {
            "slug": "mykhailo-design",
            "empathy_ratio": 0.7,
            "style": "professional",
            "unique_story": "Дизайн — це не про красу, а про розв'язання проблем людей.",
            "social_links": {"behance": "https://behance.net/mykhailo_design", "telegram": "https://t.me/mykhailo_ux"},
        },
    },
    {
        "user": {
            "email": "anna.psychology@example.com",
            "username": "anna_psychology",
            "password": "Anna2026!",
            "role": "practitioner",
        },
        "specialist": {
            "name": "Анна Довженко",
            "specialty": "Психолог",
            "service_type": "coach",
            "service_types": ["КПТ", "тривожність", "депресія", "самооцінка", "стосунки"],
            "hourly_rate": 700,
            "bio": "Клінічний психолог, КПТ-терапевт. Працюю з тривожністю, депресією, проблемами самооцінки та стосунків.",
            "is_verified": True,
            "is_active": True,
            "delivery_method": "human",
        },
        "profile": {
            "slug": "anna-psychology",
            "empathy_ratio": 0.95,
            "style": "empathetic",
            "unique_story": "Кожна людина заслуговує на підтримку. Моя мета — створити безпечний простір для змін.",
            "social_links": {"telegram": "https://t.me/anna_psy", "instagram": "https://instagram.com/anna_psychology"},
        },
    },
    {
        "user": {
            "email": "ihor.energy@example.com",
            "username": "ihor_energy",
            "password": "Ihor2026!",
            "role": "practitioner",
        },
        "specialist": {
            "name": "Ігор Енергетик",
            "specialty": "Енергопрактик",
            "service_type": "healer",
            "service_types": ["енергетичні практики", "чакри", "рейкі", "цілительство"],
            "hourly_rate": 550,
            "bio": "Сертифікований рейкі-майстер. Працюю з енергетичним балансом, чакрами, відновленням після стресу.",
            "is_verified": True,
            "is_active": True,
            "delivery_method": "human",
        },
        "profile": {
            "slug": "ihor-energy",
            "empathy_ratio": 0.85,
            "style": "calm",
            "unique_story": "Енергія — це мова тіла. Я допомагаю людям знову почути себе.",
            "social_links": {"telegram": "https://t.me/ihor_energy"},
        },
    },
]


async def seed_database():
    """Створює спеціалістів ТІЛЬКИ якщо таблиця specialists порожня."""
    async with async_session_maker() as session:
        result = await session.execute(select(func.count(Specialist.id)))
        count = result.scalar()

        if count > 0:
            logger.info(f"✅ Database already has {count} specialists — skipping seed")
            return

        logger.info("🌱 Database is empty — seeding specialists...")
        created = 0

        for data in SEED_SPECIALISTS:
            try:
                user = User(
                    email=data["user"]["email"],
                    username=data["user"]["username"],
                    password_hash=hash_password(data["user"]["password"]),  # ВИПРАВЛЕНО
                    role=data["user"]["role"],
                    is_active=True,
                )
                session.add(user)
                await session.flush()

                specialist = Specialist(
                    name=data["specialist"]["name"],
                    specialty=data["specialist"]["specialty"],
                    service_type=data["specialist"]["service_type"],
                    service_types=data["specialist"]["service_types"],
                    hourly_rate=data["specialist"]["hourly_rate"],
                    bio=data["specialist"]["bio"],
                    is_verified=data["specialist"]["is_verified"],
                    is_active=data["specialist"]["is_active"],
                    delivery_method=data["specialist"].get("delivery_method", "human"),
                    user_id=user.id,
                )
                session.add(specialist)
                await session.flush()

                profile = PractitionerProfile(
                    specialist_id=specialist.id,
                    slug=data["profile"]["slug"],
                    empathy_ratio=data["profile"].get("empathy_ratio", 0.8),
                    style=data["profile"].get("style", "warm"),
                    unique_story=data["profile"].get("unique_story", ""),
                    social_links=data["profile"].get("social_links", {}),
                    is_active=True,
                )
                session.add(profile)
                created += 1
                logger.info(f"  ✅ {data['specialist']['name']} ({data['specialist']['specialty']})")
            except Exception as e:
                logger.error(f"  ❌ Failed to seed {data['specialist']['name']}: {e}")
                continue

        await session.commit()
        logger.info(f"🌱 Seed complete: {created}/{len(SEED_SPECIALISTS)} specialists created")