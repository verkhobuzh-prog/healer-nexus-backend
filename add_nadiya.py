import asyncio
from app.database.connection import async_session_maker
from app.models.user import User
from app.models.specialist import Specialist
from app.models.practitioner_profile import PractitionerProfile
from app.services.blog_slug import generate_slug
async def create_nadiya():
    async with async_session_maker() as db:
        try:
            # 1. Створюємо юзера
            new_user = User(
                username="Nadiya Dykun",
                email="Nn.dikun@gmail.com",
                role="practitioner",
                is_active=True
            )
            db.add(new_user)
            await db.flush()
            # 2. Створюємо спеціаліста (Прибрав 'phone', щоб не було помилки)
            new_specialist = Specialist(
                user_id=new_user.id,
                name="Надія Дикун",
                bio="Психолог, нейрокоуч, астронумеролог. Засновниця майстерні змін ДивоДіва. Тел: +380958128633",
                telegram_handle="NadiyaDykun"
            )
            db.add(new_specialist)
            await db.flush()
            # 3. Створюємо SEO Профіль
            slug = f"nadiya-dykun-divodiva-{new_specialist.id}"
            new_profile = PractitionerProfile(
                specialist_id=new_specialist.id,
                slug=slug,
                project_id="healer-nexus"
            )
            db.add(new_profile)
            await db.commit()
            print(f"✅ Надія Дикун успішно додана!")
        except Exception as e:
            print(f"❌ Помилка: {e}")
            await db.rollback()
if __name__ == "__main__":
    asyncio.run(create_nadiya())
