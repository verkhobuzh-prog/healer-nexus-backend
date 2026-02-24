import asyncio
from app.database.connection import async_session_maker
from app.models.user import User
from app.models.specialist import Specialist
from app.models.practitioner_profile import PractitionerProfile
from app.services.blog_slug import generate_slug
async def create_anton():
    async with async_session_maker() as db:
        try:
            # 1. Користувач
            new_user = User(
                username="Anton Zabolotnyi", 
                email="zabolotnii333@i.ua", 
                role="practitioner",
                is_active=True
            )
            db.add(new_user)
            await db.flush()
            # 2. Спеціаліст (використовуємо існуючі поля)
            new_specialist = Specialist(
                user_id=new_user.id,
                name="Антон Заболотний",
                specialty="Цілитель, регресолог, кармолог",
                bio="Діагностика і зцілення душі і тіла. Тел: +8613430583351",
                telegram_id="anton_miraton",  # Ваше поле в базі
                is_active=True,
                is_verified=True
            )
            db.add(new_specialist)
            await db.flush()
            # 3. SEO Профіль
            slug = f"{generate_slug(new_specialist.name)}-{new_specialist.id}"
            new_profile = PractitionerProfile(
                specialist_id=new_specialist.id, 
                slug=slug, 
                project_id="healer-nexus"
            )
            db.add(new_profile)
            await db.commit()
            print(f"✅ Антон успішно доданий!")
            print(f"🔗 SEO Slug: {slug}")
        except Exception as e:
            print(f"❌ Помилка: {e}")
if __name__ == "__main__":
    asyncio.run(create_anton())
