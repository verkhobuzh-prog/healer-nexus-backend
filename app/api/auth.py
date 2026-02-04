from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import get_db
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from app.models.user import User, UserRole
from sqlalchemy import select

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    role: UserRole = UserRole.CLIENT

@router.post("/register")
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=request.email,
        username=request.username,
        hashed_password=pwd_context.hash(request.password),
        role=request.role
    )
    db.add(user)
    await db.commit()
    return {"status": "user created", "email": user.email}
