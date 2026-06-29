from sqlalchemy.ext.asyncio import AsyncSession
from models.audit import AuditLog
from fastapi import Request
import structlog

logger = structlog.get_logger()


async def log_audit_event(
    db: AsyncSession,
    action: str,
    user_id: str | None = None,
    request: Request | None = None,
    details: dict | None = None,
):
    """Log security and user events into audit log."""
    try:
        ip_address = None
        user_agent = None
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")

        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )
        db.add(audit_entry)
        await db.commit()
        logger.info("Audit event logged", action=action, user_id=user_id)
    except Exception as e:
        logger.error("Failed to log audit event", action=action, error=str(e))
        try:
            await db.rollback()
        except Exception:
            pass
