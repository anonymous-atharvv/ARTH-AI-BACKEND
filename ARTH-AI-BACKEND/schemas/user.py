# backend/schemas/user.py
from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    phone_number: str
    name: Optional[str] = None
    preferred_language: str = "hi"
    business_type: Optional[str] = None
    business_location: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    phone_number: str
    name: Optional[str] = None
    preferred_language: str = "hi"
    business_type: Optional[str] = None
    business_location: Optional[str] = None
    onboarding_complete: bool = False
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}
