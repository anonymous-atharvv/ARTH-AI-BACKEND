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
from cache import get_redis
from config import settings
import json

logger = structlog.get_logger()


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
        res = await db.execute(select(User.id, User.preferred_language, User.phone_number, User.name).where(User.onboarding_complete))
        users = res.all()
    
    wa = WhatsAppService()
    seven_days_ago = (date.today() - timedelta(days=7)).isoformat()
    
    for user_id, preferred_language, phone_number, user_name in users:
        try:
            async with AsyncSessionLocal() as db:
                tx_res = await db.execute(
                    select(Transaction).where(
                        Transaction.user_id == user_id,
                        Transaction.transaction_date >= seven_days_ago
                    )
                )
                txs = tx_res.scalars().all()
            
            income = sum(float(t.amount) for t in txs if t.type == "income")
            expense = sum(float(t.amount) for t in txs if t.type == "expense")
            saving = income - expense
            
            if preferred_language == "hi":
                msg = (
                    f"📊 *Weekly Summary for {user_name or 'Business'}* 📊\n\n"
                    f"Namaste! Is hafte ka lekha-jokha:\n"
                    f"🔹 Total Income: ₹{income:,.2f}\n"
                    f"🔸 Total Expense: ₹{expense:,.2f}\n"
                    f"💵 Net Saving: ₹{saving:,.2f}\n\n"
                    f"ArthAI ke saath tracking karte rahein aur apna business badhaein! 🚀"
                )
            else:
                msg = (
                    f"📊 *Weekly Summary for {user_name or 'Business'}* 📊\n\n"
                    f"Here is your financial activity for the past 7 days:\n"
                    f"🔹 Total Income: ₹{income:,.2f}\n"
                    f"🔸 Total Expense: ₹{expense:,.2f}\n"
                    f"💵 Net Saving: ₹{saving:,.2f}\n\n"
                    f"Keep tracking with ArthAI to grow your business! 🚀"
                )
            
            await wa.send_message(phone_number, msg)
            logger.info("Sent weekly summary", user_id=user_id)
        except Exception as e:
            logger.error("Failed to send weekly summary", user_id=user_id, error=str(e))


async def _run_daily_anomaly_checks_async():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User.id, User.preferred_language, User.phone_number))
        users = res.all()
    
    wa = WhatsAppService()
    today = date.today().isoformat()
    
    for user_id, preferred_language, phone_number in users:
        try:
            async with AsyncSessionLocal() as db:
                today_res = await db.execute(
                    select(Transaction).where(
                        Transaction.user_id == user_id,
                        Transaction.transaction_date == today
                    )
                )
                today_txs = today_res.scalars().all()
            
            if not today_txs:
                continue
            
            for tx in today_txs:
                if not tx.category_code:
                    continue
                
                async with AsyncSessionLocal() as db:
                    history_res = await db.execute(
                        select(Transaction.amount).where(
                            Transaction.user_id == user_id,
                            Transaction.category_code == tx.category_code,
                            Transaction.transaction_date < today
                        )
                    )
                    amounts = history_res.scalars().all()
                
                if len(amounts) < 3:
                    continue
                
                avg_amount = sum(amounts) / len(amounts)
                if tx.amount > 5 * avg_amount and tx.amount > 1000:
                    if preferred_language == "hi":
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
                    await wa.send_message(phone_number, msg)
                    logger.info("Sent anomaly alert", user_id=user_id, tx_id=tx.id)
        except Exception as e:
            logger.error("Failed to run anomaly checks for user", user_id=user_id, error=str(e))


async def _nightly_cache_warming_async():
    try:
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(User.id))
            user_ids = res.scalars().all()
    except Exception as db_err:
        logger.error("Failed to fetch users for nightly cache warming", error=str(db_err))
        return
    
    try:
        redis = await get_redis()
    except Exception as redis_err:
        logger.error("Failed to connect to Redis for cache warming", error=str(redis_err))
        redis = None
    
    for user_id in user_ids:
        try:
            async with AsyncSessionLocal() as db:
                engine = ArthScoreEngine(db)
                result = await engine.calculate(str(user_id), lookback_days=90)
            
            if redis:
                await redis.setex(f"arthscore:{user_id}", 86400, json.dumps(result))
                logger.info("Warmed ArthScore cache", user_id=user_id)
            else:
                logger.warning("Redis not available, skipped caching warmed score", user_id=user_id)
        except Exception as e:
            logger.error("Failed to warm ArthScore cache", user_id=user_id, error=str(e))

