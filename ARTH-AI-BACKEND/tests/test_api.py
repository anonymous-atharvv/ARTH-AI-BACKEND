# backend/tests/test_api.py
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"

async def test_readiness_probe(client: AsyncClient):
    response = await client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}

async def test_auth_send_otp(client: AsyncClient):
    response = await client.post("/api/v1/auth/send-otp", json={"phone": "+919876543210"})
    assert response.status_code == 200
    assert response.json()["message"] == "OTP sent"

async def test_demo_flow(client: AsyncClient):
    # 1. Seed demo
    seed_res = await client.post("/api/v1/demo/seed")
    assert seed_res.status_code == 200
    seed_data = seed_res.json()
    assert seed_data["user"] == "Raju Kumar"
    
    # 2. Get demo token
    token_res = await client.post("/api/v1/auth/demo-token")
    assert token_res.status_code == 200
    token_data = token_res.json()
    assert "access_token" in token_data
    assert token_data["user_id"] == "raju-demo-001"
