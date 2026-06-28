# backend/schemas/report.py
from pydantic import BaseModel
from typing import Optional


class PassportResponse(BaseModel):
    download_url: str
    arthascore: int
    loan_eligible: float
    expires_at: str
