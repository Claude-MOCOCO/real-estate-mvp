import logging
import time

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

_start_time = time.time()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    uptime_seconds = round(time.time() - _start_time)
    base = {
        "version": "0.1.0",
        "environment": settings.environment,
        "uptime_seconds": uptime_seconds,
    }

    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected", **base}
    except Exception as e:
        logger.error("Health check DB 연결 실패: %s", e)
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "disconnected", **base},
        )
