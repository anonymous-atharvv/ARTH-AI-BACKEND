# backend/routes/auth.py
"""Phone OTP authentication flow."""
import random, string
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from database import get_db
from models.user import User
from middleware.auth import create_access_token
from middleware.rate_limit import limiter
import redis.asyncio as aioredis
from config import settings
import structlog

router = APIRouter()
logger = structlog.get_logger()

# OTP store (Redis, 5-minute expiry)
async def get_redis():
    return await aioredis.from_url(settings.REDIS_URL)


class SendOTPRequest(BaseModel):
    phone: str  # E.164 format: +919876543210


class VerifyOTPRequest(BaseModel):
    phone: str
    otp: str


@router.post("/send-otp")
@limiter.limit("5/hour")
async def send_otp(request: Request, otp_req: SendOTPRequest):
    """Send 6-digit OTP via WhatsApp/SMS."""
    # Generate OTP
    otp = "".join(random.choices(string.digits, k=6))
    
    redis = await get_redis()
    await redis.setex(f"otp:{otp_req.phone}", 300, otp)  # 5-minute expiry
    
    # In production: send via Twilio WhatsApp
    # For demo: log it
    logger.info("OTP generated", phone=otp_req.phone, otp=otp)
    
    return {"message": "OTP sent", "expires_in": 300}


@router.post("/verify-otp")
async def verify_otp(otp_req: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    """Verify OTP and return JWT token."""
    redis = await get_redis()
    stored_otp = await redis.get(f"otp:{otp_req.phone}")
    
    if not stored_otp or stored_otp.decode() != otp_req.otp:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    await redis.delete(f"otp:{otp_req.phone}")
    
    # Get or create user
    result = await db.execute(select(User).where(User.phone_number == otp_req.phone))
    user = result.scalar_one_or_none()
    
    is_new_user = False
    if not user:
        user = User(phone_number=otp_req.phone, preferred_language="hi")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        is_new_user = True
    
    token = create_access_token(str(user.id), user.phone_number)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "is_new_user": is_new_user,
        "onboarding_complete": user.onboarding_complete,
    }


@router.post("/demo-token")
async def get_demo_token(db: AsyncSession = Depends(get_db)):
    """Get a pre-authenticated token for the demo user (disable in production)."""
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Demo mode is disabled")
    
    result = await db.execute(select(User).where(User.id == "raju-demo-001"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Demo not seeded. Call /api/demo/seed first.")
    
    token = create_access_token("raju-demo-001", "+919876543210")
    return {"access_token": token, "token_type": "bearer", "user_id": "raju-demo-001"}
