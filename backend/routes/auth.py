# backend/routes/auth.py
"""Phone OTP authentication flow."""
import random, string
import re
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, field_validator
from database import get_db
from models.user import User
from middleware.auth import create_access_token, verify_token
from middleware.rate_limit import limiter
from cache import get_redis
from config import settings
import structlog
from datetime import datetime

router = APIRouter()
logger = structlog.get_logger()


class SendOTPRequest(BaseModel):
    phone: str  # E.164 format: +919876543210

    @field_validator("phone")
    @classmethod
    def validate_e164(cls, v):
        cleaned = re.sub(r"[^\d+]", "", v)
        if not cleaned.startswith("+"):
            cleaned = "+" + cleaned
        if not re.match(r"^\+[1-9]\d{9,14}$", cleaned):
            raise ValueError("Phone number must be in E.164 format (e.g., +919876543210)")
        return cleaned


class VerifyOTPRequest(BaseModel):
    phone: str
    otp: str

    @field_validator("phone")
    @classmethod
    def validate_e164(cls, v):
        cleaned = re.sub(r"[^\d+]", "", v)
        if not cleaned.startswith("+"):
            cleaned = "+" + cleaned
        if not re.match(r"^\+[1-9]\d{9,14}$", cleaned):
            raise ValueError("Phone number must be in E.164 format (e.g., +919876543210)")
        return cleaned


@router.post("/send-otp")
@limiter.limit("5/hour")
async def send_otp(request: Request, otp_req: SendOTPRequest):
    """Send 6-digit OTP via WhatsApp/SMS."""
    # Generate OTP
    otp = "".join(random.choices(string.digits, k=6))
    
    redis = await get_redis()
    await redis.setex(f"otp:{otp_req.phone}", 300, otp)  # 5-minute expiry
    
    # In production: send via Twilio WhatsApp
    # For demo: log it suffix for privacy, never log OTP
    logger.info("OTP sent", phone_suffix=otp_req.phone[-4:], otp_length=len(otp))
    
    return {"message": "OTP sent", "expires_in": 300}


@router.post("/verify-otp")
@limiter.limit("10/hour")
async def verify_otp(request: Request, otp_req: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    """Verify OTP and return JWT token."""
    redis = await get_redis()
    stored_otp = await redis.get(f"otp:{otp_req.phone}")
    
    stored_otp_str = stored_otp.decode() if isinstance(stored_otp, bytes) else stored_otp
    if not stored_otp_str or stored_otp_str != otp_req.otp:
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
    
    from services.audit import log_audit_event
    await log_audit_event(
        db,
        action="user_login_otp",
        user_id=str(user.id),
        request=request,
        details={"phone_suffix": otp_req.phone[-4:]}
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "is_new_user": is_new_user,
        "onboarding_complete": user.onboarding_complete,
    }


@router.post("/demo-token")
async def get_demo_token(request: Request, db: AsyncSession = Depends(get_db)):
    """Get a pre-authenticated token for the demo user (disable in production)."""
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Demo mode is disabled")
    
    result = await db.execute(select(User).where(User.id == "raju-demo-001"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Demo not seeded. Call /api/demo/seed first.")
    
    token = create_access_token("raju-demo-001", "+919876543210")
    
    from services.audit import log_audit_event
    await log_audit_event(
        db,
        action="user_login_demo",
        user_id="raju-demo-001",
        request=request,
        details={}
    )
    
    return {"access_token": token, "token_type": "bearer", "user_id": "raju-demo-001"}


@router.post("/logout")
async def logout(request: Request, token: dict = Depends(verify_token), db: AsyncSession = Depends(get_db)):
    jti = token.get("jti")
    if jti:
        redis = await get_redis()
        exp_timestamp = token.get("exp")
        if exp_timestamp:
            ttl = int(exp_timestamp - datetime.utcnow().timestamp())
            if ttl > 0:
                await redis.setex(f"revoked_token:{jti}", ttl, "1")
    
    from services.audit import log_audit_event
    await log_audit_event(
        db,
        action="user_logout",
        user_id=token.get("sub"),
        request=request,
        details={"jti": jti}
    )
    return {"message": "Logged out successfully"}



