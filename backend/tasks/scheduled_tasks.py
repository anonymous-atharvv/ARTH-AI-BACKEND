# backend/tasks/scheduled_tasks.py
from tasks.celery_app import celery_app
import asyncio
import structlog
from datetime import date, timedelta
from database import AsyncSessionLocal
from models.user import User
from models.transaction import Transaction
from sqlalchemy import select, func
from services.whatsapp import WhatsAppService
from agents.arthascore import ArthScoreEngine
import redis.asyncio as aioredis
from config import settings
import json

logger = structlog.get_logger()

async def get_redis():
    return await aioredis.from_url(settings.REDIS_URL)

@celery_app.task(name="send_weekly_summary")
def send_weekly_summary():
    """Weekly task to send income/expense summaries to users on Mondays."""
    asyncio.run(_send_weekly_summary_async())

@celery_app.task(name="run_daily_anomaly_checks")
def run_daily_anomaly_checks():
    """Daily task to scan today's transactions and flag anomalies."""
    asyncio.run(_run_daily_anomaly_checks_async())

@celery_app.task(name="nightly_cache_warming")
def nightly_cache_warming():
    """Nightly task to warm the ArthScore Redis cache for active users."""
    asyncio.run(_nightly_cache_warming_async())

async def _send_weekly_summary_async():
    async with AsyncSessionLocal() as db:
        # Fetch onboarding-complete users
        res = await db.execute(select(User).where(User.onboarding_complete == True))
        users = res.scalars().all()
        
        wa = WhatsAppService()
        seven_days_ago = (date.today() - timedelta(days=7)).isoformat()
        
        for user in users:
            # Query income and expenses for past 7 days
            tx_res = await db.execute(
                select(Transaction).where(
                    Transaction.user_id == user.id,
                    Transaction.transaction_date >= seven_days_ago
                )
            )
            txs = tx_res.scalars().all()
            
            income = sum(float(t.amount) for t in txs if t.type == "income")
            expense = sum(float(t.amount) for t in txs if t.type == "expense")
            saving = income - expense
            
            # Format message based on language
            if user.preferred_language == "hi":
                msg = (
                    f"📊 *Weekly Summary for {user.name or 'Business'}* 📊\n\n"
                    f"Namaste! Is hafte ka lekha-jokha:\n"
                    f"🔹 Total Income: ₹{income:,.2f}\n"
                    f"🔸 Total Expense: ₹{expense:,.2f}\n"
                    f"💵 Net Saving: ₹{saving:,.2f}\n\n"
                    f"ArthAI ke saath tracking karte rahein aur apna business badhaein! 🚀"
                )
            else:
                msg = (
                    f"📊 *Weekly Summary for {user.name or 'Business'}* 📊\n\n"
                    f"Here is your financial activity for the past 7 days:\n"
                    f"🔹 Total Income: ₹{income:,.2f}\n"
                    f"🔸 Total Expense: ₹{expense:,.2f}\n"
                    f"💵 Net Saving: ₹{saving:,.2f}\n\n"
                    f"Keep tracking with ArthAI to grow your business! 🚀"
                )
            
            try:
                await wa.send_message(user.phone_number, msg)
                logger.info("Sent weekly summary", user_id=user.id, phone=user.phone_number)
            except Exception as e:
                logger.error("Failed to send weekly summary", user_id=user.id, error=str(e))

async def _run_daily_anomaly_checks_async():
    async with AsyncSessionLocal() as db:
        # Fetch users
        res = await db.execute(select(User))
        users = res.scalars().all()
        
        wa = WhatsAppService()
        today = date.today().isoformat()
        
        for user in users:
            # Fetch today's transactions
            today_res = await db.execute(
                select(Transaction).where(
                    Transaction.user_id == user.id,
                    Transaction.transaction_date == today
                )
            )
            today_txs = today_res.scalars().all()
            
            if not today_txs:
                continue
            
            # For each transaction, compare with category history
            for tx in today_txs:
                if not tx.category_code:
                    continue
                # Fetch category history excluding today
                history_res = await db.execute(
                    select(Transaction.amount).where(
                        Transaction.user_id == user.id,
                        Transaction.category_code == tx.category_code,
                        Transaction.transaction_date < today
                    )
                )
                amounts = history_res.scalars().all()
                if len(amounts) < 3:
                    continue
                
                avg_amount = sum(amounts) / len(amounts)
                # If transaction is 5 times the historical average, trigger anomaly
                if tx.amount > 5 * avg_amount and tx.amount > 1000:
                    # Anomaly detected!
                    if user.preferred_language == "hi":
                        msg = (
                            f"⚠️ *ArthAI Anomaly Alert* ⚠️\n\n"
                            f"Raju bhai, aaj aapne ek bada kharch/income record kiya hai:\n"
                            f"₹{tx.amount:,.2f} ({tx.category_code or 'Other'}).\n"
                            f"Ye aapke average ₹{avg_amount:,.2f} se kaafi zyada hai. "
                            f"Agar ye galat hai toh WhatsApp par reply karein."
                        )
                    else:
                        msg = (
                            f"⚠️ *ArthAI Anomaly Alert* ⚠️\n\n"
                            f"We detected an unusually large transaction today:\n"
                            f"₹{tx.amount:,.2f} under category '{tx.category_code or 'Other'}'.\n"
                            f"Your historical average is ₹{avg_amount:,.2f}. "
                            f"If this is a mistake, please reply to correct it."
                        )
                    try:
                        await wa.send_message(user.phone_number, msg)
                        logger.info("Sent anomaly alert", user_id=user.id, tx_id=tx.id)
                    except Exception as e:
                        logger.error("Failed to send anomaly alert", user_id=user.id, error=str(e))

async def _nightly_cache_warming_async():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User))
        users = res.scalars().all()
        
        redis = await get_redis()
        engine = ArthScoreEngine(db)
        
        for user in users:
            try:
                # Pre-calculate score
                result = await engine.calculate(str(user.id), lookback_days=90)
                # Warm cache (save for 24 hours since it runs nightly)
                await redis.setex(f"arthscore:{user.id}", 86400, json.dumps(result))
                logger.info("Warmed ArthScore cache", user_id=user.id)
            except Exception as e:
                logger.error("Failed to warm ArthScore cache", user_id=user.id, error=str(e))
