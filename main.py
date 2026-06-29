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

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import structlog
import logging
import os

from config import settings

def configure_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer() if settings.ENVIRONMENT == "production"
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
    )

configure_logging()
logger = structlog.get_logger()

from database import create_db_tables
from middleware.rate_limit import limiter, rate_limit_error_handler
from middleware.security_headers import SecurityHeadersMiddleware
from middleware.request_id import RequestIDMiddleware
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
    from cache import close_redis, ping_redis
    redis_ready = await ping_redis()
    if settings.REDIS_REQUIRED and not redis_ready:
        raise RuntimeError("REDIS_REQUIRED=true but Redis is unavailable")
    
    if settings.ENVIRONMENT != "production":
        await create_db_tables()
    # Seed categories on startup
    await _seed_categories()
    yield
    # Close Redis pool
    await close_redis()
    logger.info("ArthAI backend shutting down")


app = FastAPI(
    title="ArthAI API",
    description="India's Agentic Financial Intelligence Layer for the Informal Economy",
    version="3.0.0",
    lifespan=lifespan,
)

# Request ID Middleware (first in stack)
app.add_middleware(RequestIDMiddleware)

# Rate Limiting Setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_error_handler)
app.add_middleware(SlowAPIMiddleware)

# Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Route Registration ─────────────────────────────────────────────
from routes import webhook, transactions, analytics, score, reports, users, demo, marketplace, auth, aa

app.include_router(webhook.router, prefix="/webhook", tags=["WhatsApp Webhook"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["Transactions"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(score.router, prefix="/api/v1/score", tags=["ArthScore"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(demo.router, prefix="/api/v1/demo", tags=["Demo"])
app.include_router(marketplace.router, prefix="/api/v1/marketplace", tags=["Marketplace"])
app.include_router(aa.router, prefix="/api/v1/aa", tags=["Account Aggregator"])


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled request exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


# Mount static files directory
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/health")
async def health_check():
    """Enhanced health check with database, Redis, and config verification."""
    from database import AsyncSessionLocal
    from sqlalchemy import text
    from cache import ping_redis
    
    checks = {}

    # Database check
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception as e:
        checks["database"] = f"error: {str(e)[:100]}"
        logger.error("Health check database failure", error=str(e))

    # Redis check
    try:
        checks["redis"] = "connected" if await ping_redis() else "unavailable"
    except Exception as e:
        checks["redis"] = f"error: {str(e)[:100]}"
        logger.error("Health check Redis failure", error=str(e))

    # Configuration checks
    checks["openai_configured"] = bool(settings.OPENAI_API_KEY)
    checks["twilio_configured"] = bool(settings.TWILIO_AUTH_TOKEN)
    checks["sarvam_configured"] = bool(settings.SARVAM_API_KEY)

    redis_ok = checks.get("redis") == "connected" or not settings.REDIS_REQUIRED
    status = "healthy" if checks.get("database") == "connected" and redis_ok else "degraded"

    return {
        "status": status,
        "checks": checks,
        "database": checks.get("database"),
        "redis": checks.get("redis"),
        "service": "ArthAI Backend",
        "version": "3.0.0",
        "environment": settings.ENVIRONMENT,
        "redis_required": settings.REDIS_REQUIRED,
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
Instrumentator().instrument(app).expose(app, endpoint="/metrics-internal")



async def _seed_categories():
    """Seed category master data if not exists."""
    from database import AsyncSessionLocal
    from models.category import Category
    from sqlalchemy import select
    from sqlalchemy.exc import IntegrityError

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
        created = 0
        for code, name_en, name_hi, type_, icon in CATEGORIES:
            result = await db.execute(select(Category).where(Category.code == code))
            if result.scalar_one_or_none() is None:
                db.add(Category(
                    code=code, name_en=name_en, name_hi=name_hi,
                    type=type_, icon=icon
                ))
                created += 1
        if created:
            try:
                await db.commit()
                logger.info("Categories seeded", count=created)
            except IntegrityError:
                await db.rollback()
                logger.info("Categories already seeded by another worker")
