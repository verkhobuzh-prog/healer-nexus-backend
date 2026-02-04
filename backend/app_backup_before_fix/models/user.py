from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.models.base import Base, TimestampMixin  # Додали Mixin

class User(Base, TimestampMixin):  # Успадковуємо час створення автоматично
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    
    # Поле created_at тепер береться з TimestampMixin, 
    # тому тут його можна видалити, щоб не було дублювання.

    # Фінанси та ліміти
    balance = Column(Float, default=0.0)
    requests_left = Column(Integer, default=5)   # Безкоштовні запити
    total_requests = Column(Integer, default=0)  # Всього запитів

    # Підписка
    is_subscribed = Column(Boolean, default=False)
    subscription_end = Column(DateTime, nullable=True)

    # Зв'язки
    # Переконайтеся, що в моделі Message також є back_populates="user"
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")

    def can_make_request(self) -> bool:
        """Перевірка доступності запиту"""
        # 1. Якщо є активна підписка
        if self.is_subscribed and self.subscription_end:
            # Працюємо з aware datetime (UTC)
            if self.subscription_end.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
                return True
        
        # 2. Якщо залишилися безкоштовні запити
        return self.requests_left > 0
