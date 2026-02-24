import asyncio
from app.database.connection import async_session_maker
from app.models.user import User
from app.models.specialist import Specialist
from app.models.practitioner_profile import PractitionerProfile
from app.services.blog_slug import generate_slug
async def create_anton():
    async with async_session_maker() as db:
        # 1. Створюємо юзера
        new_user = User(
            username="Anton Zabolotnyi",
            email="zabolotnii333@i.ua",
            role="practitioner",
            is_active=True
        )
        db.add(new_user)
        await db.flush() # Отримуємо ID юзера
        # 2. Створюємо спеціаліста
        new_specialist = Specialist(
            user_id=new_user.id,
            name="Антон Заболотний",
            bio="цілитель, регресолог, кармолог. діагностика і зцілення душі і тіла",
            phone="+8613430583351",
            telegram_handle="anton_miraton"
        )
        db.add(new_specialist)
        await db.flush()
        # 3. Створюємо SEO-профіль (slug)
        slug = f"{generate_slug(new_specialist.name)}-{new_specialist.id}"
        new_profile = PractitionerProfile(
            specialist_id=new_specialist.id,
            slug=slug,
            project_id="healer-nexus"
        )
        db.add(new_profile)
        await db.commit()
        print(f"✅ Антон Заболотний створений! SEO URL: /specialists/{slug}")
if __name__ == "__main__":
    asyncio.run(create_anton())
