# backend/main.py
"""
ArthAI Backend — FastAPI Application Entry Point
India's Agentic Financial Intelligence Layer for the Informal Economy
"""
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from prometheus_fastapi_instrumentator import Instrumentator

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import structlog
import os

from config import settings
from database import create_db_tables
from middleware.rate_limit import limiter, rate_limit_error_handler
from middleware.security_headers import SecurityHeadersMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

logger = structlog.get_logger()

# ─── Initialize Sentry ──────────────────────────────────────────────
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
            CeleryIntegration(),
        ],
        traces_sample_rate=1.0,
    )
    logger.info("Sentry initialized")


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
    version="3.0.0",
    lifespan=lifespan,
)

# Rate Limiting Setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_error_handler)
app.add_middleware(SlowAPIMiddleware)

# Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Route Registration ─────────────────────────────────────────────
from routes import webhook, transactions, analytics, score, reports, users, demo, marketplace, auth

app.include_router(webhook.router, prefix="/webhook", tags=["WhatsApp Webhook"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["Transactions"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(score.router, prefix="/api/v1/score", tags=["ArthScore"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(demo.router, prefix="/api/v1/demo", tags=["Demo"])
app.include_router(marketplace.router, prefix="/api/v1/marketplace", tags=["Marketplace"])

# Mount static files directory
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/health")
async def health_check():
    """Enhanced health check with database verification."""
    from database import AsyncSessionLocal
    from sqlalchemy import text
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        db_ok = False
        logger.error("Health check database failure", error=str(e))
        
    return {
        "status": "healthy" if db_ok else "unhealthy",
        "database": "connected" if db_ok else "disconnected",
        "service": "ArthAI Backend",
        "version": "3.0.0"
    }


@app.get("/ready")
async def readiness_probe():
    """Readiness probe for K8s / load balancers."""
    from database import AsyncSessionLocal
    from sqlalchemy import text
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        logger.error("Readiness check database failure", error=str(e))
        return Response(content="Service Unavailable", status_code=503)


# Prometheus Instrumentation
Instrumentator().instrument(app).expose(app)


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
