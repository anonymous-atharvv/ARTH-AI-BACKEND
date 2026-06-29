# backend/tasks/aa_tasks.py
from tasks.celery_app import celery_app
import asyncio
import structlog

logger = structlog.get_logger()

@celery_app.task(
    name="fetch_and_import_aa_data",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
)
def fetch_and_import_aa_data(self, consent_handle: str, user_id: str):
    """
    Asynchronously fetch and import financial data from Account Aggregator.
    """
    try:
        asyncio.run(_fetch_and_import_async(consent_handle, user_id))
    except Exception as exc:
        logger.error("AA fetch and import failed, retrying",
                     attempt=self.request.retries,
                     error=str(exc))
        raise self.retry(exc=exc)


async def _fetch_and_import_async(consent_handle: str, user_id: str):
    from database import AsyncSessionLocal
    from services.account_aggregator import AccountAggregatorService
    from models.transaction import Transaction
    from services.analytics import AnalyticsService
    from services.cache_manager import invalidate_user_caches
    from datetime import datetime

    service = AccountAggregatorService()
    transactions_data = await service.fetch_fi_data(consent_handle)

    if not transactions_data:
        logger.info("No transaction data returned from Account Aggregator", consent_handle=consent_handle)
        return

    async with AsyncSessionLocal() as db:
        imported_count = 0
        for tx_data in transactions_data:
            tx = Transaction(
                user_id=user_id,
                amount=tx_data["amount"],
                type=tx_data["type"],
                category_code=tx_data["category_code"],
                counterparty=tx_data["counterparty"],
                description=tx_data["description"],
                payment_method=tx_data["payment_method"],
                transaction_date=datetime.fromisoformat(tx_data["transaction_date"]).date(),
                source="account_aggregator",
                raw_input=tx_data["raw_input"],
                confidence_score=tx_data["confidence_score"],
                verified=True
            )
            db.add(tx)
            imported_count += 1
        
        await db.commit()
        logger.info("Successfully imported transactions from AA", user_id=user_id, count=imported_count)

        # Refresh analytics cache
        analytics = AnalyticsService(db)
        await analytics.refresh_cache(user_id)

    # Invalidate user cache (Redis)
    await invalidate_user_caches(user_id)
