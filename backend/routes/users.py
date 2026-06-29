# backend/routes/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.user import User
from schemas.user import UserCreate, UserResponse
from middleware.auth import get_current_user_id, get_current_phone
from config import settings

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user (public/pre-auth)."""
    result = await db.execute(
        select(User).where(User.phone_number == user_data.phone_number)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    user = User(**user_data.model_dump())
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/{phone}", response_model=UserResponse)
async def get_user_by_phone(
    phone: str,
    current_phone: str = Depends(get_current_phone),
    db: AsyncSession = Depends(get_db)
):
    """Get user by phone number (secured)."""
    if settings.ENVIRONMENT == "production":
        if phone != current_phone:
            raise HTTPException(status_code=403, detail="Access denied")
    elif phone != current_phone and not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Forbidden")


    result = await db.execute(select(User).where(User.phone_number == phone))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
