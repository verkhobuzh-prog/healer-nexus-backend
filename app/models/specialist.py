from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Text, BigInteger, Boolean, Float, JSON
from app.models.base import Base, TimestampMixin

class Specialist(Base, TimestampMixin):
    """Модель спеціаліста (людина або AI)"""
    __tablename__ = "specialists"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # ✅ Синхронізовано: service_type замість niche
    service_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="healer | coach | teacher_math | interior_designer | 3d_modeling | web_development"
    )
    
    # ✅ НОВЕ поле
    service_types: Mapped[list] = mapped_column(
        JSON,
        nullable=True,
        default=list,
        comment='["healer", "meditation"] - список ніш'
    )

    # ✅ Метод доставки послуги
    delivery_method: Mapped[str] = mapped_column(
        String(50),
        default="human",
        nullable=False,
        comment="human | ai_assisted | fully_ai"
    )

    specialty: Mapped[str] = mapped_column(String(200), nullable=False)
    hourly_rate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Геолокація
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Контакти - ✅ BigInteger для Telegram ID (виправлено дублювання)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ✅ AI можливості
    is_ai_powered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_capabilities: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Статус
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        # ✅ Виправлено закриття рядка
        return f"<Specialist(id={self.id}, name={self.name}, service={self.service_type}, delivery={self.delivery_method})>"