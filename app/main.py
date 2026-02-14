import logging

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.kakao import router as kakao_router
from app.api.properties import router as properties_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="부동산 개인비서 MVP",
    description="공인중개사 전용 AI 비서 — 카카오톡 채널봇 + FastAPI",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(kakao_router)
app.include_router(properties_router)
