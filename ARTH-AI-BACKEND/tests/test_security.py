# backend/tests/test_security.py
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_protected_endpoints_require_auth(client: AsyncClient):
    """Financial endpoints must reject unauthenticated requests."""
    endpoints = [
        ("GET", "/api/v1/analytics/summary/raju-demo-001"),
        ("GET", "/api/v1/score/raju-demo-001"),
        ("POST", "/api/v1/reports/passport/raju-demo-001"),
    ]
    for method, path in endpoints:
        response = await client.request(method, path)
        assert response.status_code in (401, 403), \
            f"Endpoint {method} {path} returned {response.status_code} without auth"


async def test_security_headers_present(client: AsyncClient):
    """Security headers must be present on all responses."""
    response = await client.get("/health")
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "Strict-Transport-Security" in response.headers


async def test_transaction_amount_validation(client: AsyncClient):
    """Negative transaction amounts must be rejected."""
    await client.post("/api/v1/demo/seed")
    token_res = await client.post("/api/v1/auth/demo-token")
    token = token_res.json()["access_token"]

    response = await client.post(
        "/api/v1/transactions/raju-demo-001",
        json={"amount": -500.0, "type": "income", "source": "text",
              "transaction_date": "2026-06-29", "payment_method": "cash"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 422
