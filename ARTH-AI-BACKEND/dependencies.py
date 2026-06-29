# backend/dependencies.py
"""
Shared FastAPI dependency injection providers.
"""
from database import get_db

# Re-export for consistent imports across routes
__all__ = ["get_db"]
