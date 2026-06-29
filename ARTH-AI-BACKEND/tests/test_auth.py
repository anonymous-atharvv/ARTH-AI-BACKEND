# backend/tests/test_auth.py
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_send_otp_validates_phone_format(client: AsyncClient):
    """Invalid phone format must return 422."""
    response = await client.post("/api/v1/auth/send-otp", json={"phone": "not-a-phone"})
    assert response.status_code == 422  # Validation error


async def test_send_otp_accepts_e164_format(client: AsyncClient):
    """Valid E.164 phone must return 200."""
    response = await client.post("/api/v1/auth/send-otp", json={"phone": "+919876543210"})
    assert response.status_code == 200
    assert response.json()["message"] == "OTP sent"


async def test_verify_otp_wrong_code_returns_400(client: AsyncClient):
    """Wrong OTP must return 400, not 500."""
    await client.post("/api/v1/auth/send-otp", json={"phone": "+919876543210"})
    response = await client.post("/api/v1/auth/verify-otp",
                                  json={"phone": "+919876543210", "otp": "000000"})
    assert response.status_code == 400


async def test_demo_flow_end_to_end(client: AsyncClient):
    """Full demo flow: seed → token → dashboard data."""
    seed = await client.post("/api/v1/demo/seed")
    assert seed.status_code == 200

    token_res = await client.post("/api/v1/auth/demo-token")
    assert token_res.status_code == 200
    token = token_res.json()["access_token"]
    user_id = token_res.json()["user_id"]

    headers = {"Authorization": f"Bearer {token}"}
    summary = await client.get(f"/api/v1/analytics/summary/{user_id}", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["total_transactions"] > 0

    score = await client.get(f"/api/v1/score/{user_id}", headers=headers)
    assert score.status_code == 200
    assert 300 <= score.json()["score"] <= 900
