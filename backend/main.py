# backend/main.py
"""
ArthAI Backend — FastAPI Application Entry Point
India's Agentic Financial Intelligence Layer for the Informal Economy
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import structlog
import os

from config import settings
from database import create_db_tables

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ArthAI backend starting up", env=settings.ENVIRONMENT)
    await create_db_tables()
    # Seed categories on startup
    await _seed_categories()
    yield
    logger.info("ArthAI backend shutting down")


app = FastAPI(
    title="ArthAI API",
    description="India's Agentic Financial Intelligence Layer for the Informal Economy",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Route Registration ─────────────────────────────────────────────
from routes import webhook, transactions, analytics, score, reports, users, demo, marketplace

app.include_router(webhook.router, prefix="/webhook", tags=["WhatsApp Webhook"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["Transactions"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(score.router, prefix="/api/score", tags=["ArthScore"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(demo.router, prefix="/api/demo", tags=["Demo"])
app.include_router(marketplace.router, prefix="/api/marketplace", tags=["Marketplace"])

# Mount static files directory
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ArthAI Backend", "version": "1.0.0"}


async def _seed_categories():
    """Seed category master data if not exists."""
    from database import AsyncSessionLocal
    from models.category import Category
    from sqlalchemy import select

    CATEGORIES = [
        ("sales_product", "Product Sales", "माल बिक्री", "income", "🛒"),
        ("sales_service", "Service Income", "सेवा आय", "income", "⚙️"),
        ("commission", "Commission/Referral", "कमीशन", "income", "🤝"),
        ("rental_income", "Rental Income", "किराया आय", "income", "🏠"),
        ("loan_received", "Loan Received", "कर्ज मिला", "transfer", "🏦"),
        ("other_income", "Other Income", "अन्य आय", "income", "💵"),
        ("inventory", "Inventory/Stock", "माल/स्टॉक", "expense", "📦"),
        ("labor_wages", "Labor/Wages", "मजदूरी", "expense", "👷"),
        ("transport_fuel", "Transport/Fuel", "ईंधन/यातायात", "expense", "⛽"),
        ("rent_premises", "Shop/Office Rent", "दुकान/दफ्तर किराया", "expense", "🏪"),
        ("utilities", "Utilities", "बिजली/पानी", "expense", "💡"),
        ("equipment", "Equipment/Repairs", "उपकरण/मरम्मत", "expense", "🔧"),
        ("marketing", "Marketing/Promotion", "विज्ञापन", "expense", "📢"),
        ("professional_fees", "Professional Fees", "CA/वकील फीस", "expense", "📋"),
        ("loan_repayment", "Loan Repayment", "कर्ज चुकाना", "transfer", "💸"),
        ("tax_government", "Tax/Government Fees", "टैक्स/सरकारी फीस", "expense", "🏛️"),
        ("food_personal", "Food (Personal)", "खाना (व्यक्तिगत)", "expense", "🍱"),
        ("mobile_internet", "Mobile/Internet", "मोबाइल/इंटरनेट", "expense", "📱"),
        ("other_expense", "Other Expense", "अन्य खर्च", "expense", "📝"),
    ]

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Category).limit(1))
        if result.scalar_one_or_none() is None:
            for code, name_en, name_hi, type_, icon in CATEGORIES:
                db.add(Category(
                    code=code, name_en=name_en, name_hi=name_hi,
                    type=type_, icon=icon
                ))
            await db.commit()
            logger.info("Categories seeded", count=len(CATEGORIES))
