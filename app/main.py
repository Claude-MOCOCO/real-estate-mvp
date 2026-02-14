import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.kakao import router as kakao_router
from app.api.properties import router as properties_router
from app.core.database import engine
from app.schemas.kakao import KakaoResponse

logger = logging.getLogger(__name__)

_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("부동산 개인비서 MVP 시작")
    yield
    logger.info("부동산 개인비서 MVP 종료 — DB 커넥션 풀 정리")
    await engine.dispose()


app = FastAPI(
    title="부동산 개인비서 MVP",
    description="공인중개사 전용 AI 비서 — 카카오톡 채널봇 + FastAPI",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("처리되지 않은 예외: %s %s — %s", request.method, request.url.path, exc)
    if request.url.path.startswith("/kakao"):
        resp = KakaoResponse.text("죄송해요, 일시적인 오류가 발생했어요. 잠시 후 다시 시도해주세요.")
        return JSONResponse(content=resp.model_dump(exclude_none=True))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(health_router)
app.include_router(kakao_router)
app.include_router(properties_router)
