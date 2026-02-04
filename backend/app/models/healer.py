from sqlalchemy import Column, Integer, String, Text, Boolean
from app.models.base import Base

class Healer(Base):
    __tablename__ = "healers"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    niche = Column(String(50))  # healer, teacher, renovator, etc.
    specialty = Column(String(100)) # конкретна сфера
    bio = Column(Text)
    price_per_hour = Column(Integer, default=0)
    telegram_id = Column(Integer, unique=True, nullable=True)
    is_active = Column(Boolean, default=True)
