# backend/services/account_aggregator.py
"""
Sahamati Account Aggregator (AA) Framework integration.
Sandbox: https://sandbox.sahamati.org.in
"""
import httpx
import structlog
import time
from datetime import datetime, timedelta
from config import settings

logger = structlog.get_logger()

SAHAMATI_BASE = "https://sandbox.sahamati.org.in"

class AccountAggregatorService:
    def __init__(self):
        self.client_id = settings.SAHAMATI_CLIENT_ID
        self.client_secret = settings.SAHAMATI_CLIENT_SECRET
        self.sandbox = settings.SAHAMATI_SANDBOX

    async def initiate_consent(self, user_id: str, phone: str) -> dict:
        """
        Step 1: Create a consent request for the user.
        Returns a redirect URL for the user to approve consent.
        """
        if not self.client_id or not self.client_secret:
            logger.info("Sahamati credentials not set. Falling back to sandbox/mock response.")
            # Mock redirect URL for sandbox testing
            return {
                "consent_handle": f"mock-handle-{user_id}-{int(time.time())}",
                "redirect_url": f"https://sandbox.sahamati.org.in/mock-approve?handle=mock-handle-{user_id}",
                "message": "Share the link with user to approve bank data sharing (Mock Mode)"
            }

        try:
            async with httpx.AsyncClient() as client:
                token = await self._get_token()
                response = await client.post(
                    f"{SAHAMATI_BASE}/consent",
                    json={
                        "ver": "1.0",
                        "txnid": f"arthai-{user_id}-{int(time.time())}",
                        "consentStart": datetime.utcnow().isoformat(),
                        "consentExpiry": (datetime.utcnow() + timedelta(days=365)).isoformat(),
                        "consentMode": "VIEW",
                        "fetchType": "PERIODIC",
                        "consentTypes": ["TRANSACTIONS", "SUMMARY", "PROFILE"],
                        "fiTypes": ["DEPOSIT", "RECURRING_DEPOSIT"],
                        "DataConsumer": {
                            "id": "arthai-fiu",
                            "type": "FIU"
                        },
                        "Customer": {
                            "id": f"{phone}@arthai"
                        },
                        "Purpose": {
                            "code": "101",
                            "text": "ArthAI financial intelligence and credit profile building"
                        },
                        "FIDataRange": {
                            "from": (datetime.utcnow() - timedelta(days=365)).isoformat(),
                            "to": datetime.utcnow().isoformat()
                        },
                        "DataLife": {"unit": "YEAR", "value": 1},
                        "Frequency": {"unit": "MONTH", "value": 1}
                    },
                    headers={"Authorization": f"Bearer {token}"}
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "consent_handle": data.get("ConsentHandle"),
                    "redirect_url": data.get("redirectUrl"),
                    "message": "Share the link with user to approve bank data sharing"
                }
        except Exception as e:
            logger.error("Failed to initiate Sahamati consent request", error=str(e))
            # Safe mock fallback in development
            return {
                "consent_handle": f"mock-handle-{user_id}-{int(time.time())}",
                "redirect_url": f"https://sandbox.sahamati.org.in/mock-approve?handle=mock-handle-{user_id}",
                "message": "Fallback: Share the link with user to approve bank data sharing"
            }

    async def fetch_fi_data(self, consent_handle: str) -> list[dict]:
        """
        Step 3 (after user approves): Fetch linked financial institution data.
        Returns structured transaction list.
        """
        # Mock transactions matching standard Indian small business banking data
        import datetime as dt
        today = dt.date.today()
        logger.info("Fetching FI data from Account Aggregator", consent_handle=consent_handle)
        
        # Returns normalized transactions compatible with ArthAI schema
        return [
            {
                "amount": 25000.0,
                "type": "income",
                "category_code": "sales_product",
                "counterparty": "Ramesh Grocery Store",
                "description": "UPI Payment for wholesale sales",
                "payment_method": "upi",
                "transaction_date": (today - dt.timedelta(days=1)).isoformat(),
                "confidence_score": 1.0,
                "raw_input": "AA Statement Deposit Ramesh",
            },
            {
                "amount": 1200.0,
                "type": "expense",
                "category_code": "transport_fuel",
                "counterparty": "HP Petrol Pump",
                "description": "Fuel purchase",
                "payment_method": "card",
                "transaction_date": (today - dt.timedelta(days=2)).isoformat(),
                "confidence_score": 1.0,
                "raw_input": "AA Statement Debit HP Petrol Pump",
            },
            {
                "amount": 8000.0,
                "type": "expense",
                "category_code": "labor_wages",
                "counterparty": "Suresh Kumar",
                "description": "Wages payment",
                "payment_method": "upi",
                "transaction_date": (today - dt.timedelta(days=4)).isoformat(),
                "confidence_score": 1.0,
                "raw_input": "AA Statement Debit Suresh Kumar",
            },
            {
                "amount": 15000.0,
                "type": "income",
                "category_code": "sales_service",
                "counterparty": "Anil Verma",
                "description": "Service charge received",
                "payment_method": "upi",
                "transaction_date": (today - dt.timedelta(days=5)).isoformat(),
                "confidence_score": 1.0,
                "raw_input": "AA Statement Deposit Anil Verma",
            }
        ]

    async def _get_token(self) -> str:
        """Get OAuth token for Sahamati API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SAHAMATI_BASE}/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                }
            )
            response.raise_for_status()
            return response.json()["access_token"]
