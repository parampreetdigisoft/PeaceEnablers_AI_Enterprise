from fastapi import APIRouter

from app.core.config import settings
from app.database.connection import sql_engine

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": settings.db_name,
        "sql_connected": sql_engine.test_connection(),
    }
