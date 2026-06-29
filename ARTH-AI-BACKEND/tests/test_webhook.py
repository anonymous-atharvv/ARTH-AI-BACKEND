# backend/tests/test_webhook.py
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_webhook_returns_twiml_xml(client: AsyncClient):
    """Webhook must return valid TwiML XML with 200 status."""
    response = await client.post(
        "/webhook/whatsapp",
        data={"From": "whatsapp:+919876543210", "Body": "Aaj ₹500 ki sale hui", "NumMedia": "0"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    assert "<?xml" in response.text
    assert "<Response>" in response.text


async def test_webhook_handles_empty_body(client: AsyncClient):
    """Webhook must not crash on empty message body."""
    response = await client.post(
        "/webhook/whatsapp",
        data={"From": "whatsapp:+919876543210", "Body": "", "NumMedia": "0"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
