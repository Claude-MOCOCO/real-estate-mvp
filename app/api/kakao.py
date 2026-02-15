"""카카오 챗봇 스킬 서버 엔드포인트"""

import asyncio
import logging
import time
from hmac import compare_digest

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db, get_new_session
from app.schemas.kakao import KakaoRequest, KakaoResponse
from app.services.assistant import handle_utterance

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/kakao", tags=["kakao"])

# --- 인메모리 Rate Limiter (동일 사용자 초당 2회 제한) ---
_rate_limit: dict[str, list[float]] = {}
_RATE_LIMIT_MAX = 2
_RATE_LIMIT_WINDOW = 1.0  # 초


def _is_rate_limited(user_id: str) -> bool:
    """사용자별 초당 요청 횟수 체크. 제한 초과 시 True 반환."""
    now = time.monotonic()
    timestamps = _rate_limit.get(user_id, [])

    # 윈도우 밖 타임스탬프 제거
    timestamps = [t for t in timestamps if now - t < _RATE_LIMIT_WINDOW]

    if len(timestamps) >= _RATE_LIMIT_MAX:
        _rate_limit[user_id] = timestamps
        return True

    timestamps.append(now)
    _rate_limit[user_id] = timestamps

    # 메모리 누수 방지: 오래된 사용자 정리 (1000명 초과 시)
    if len(_rate_limit) > 1000:
        cutoff = now - _RATE_LIMIT_WINDOW * 10
        stale = [k for k, v in _rate_limit.items() if not v or v[-1] < cutoff]
        for k in stale:
            del _rate_limit[k]

    return False


async def verify_kakao_skill_secret(request: Request):
    """카카오 스킬 시크릿 검증.

    - KAKAO_SKILL_SECRET이 설정되지 않으면 검증 건너뜀 (개발 모드)
    - 설정되어 있으면 요청 헤더의 X-Kakao-Skill-Secret과 비교
    """
    if not settings.kakao_skill_secret:
        return
    header_secret = request.headers.get("X-Kakao-Skill-Secret", "")
    if not header_secret or not compare_digest(header_secret, settings.kakao_skill_secret):
        logger.warning("카카오 스킬 시크릿 검증 실패: ip=%s", request.client.host if request.client else "unknown")
        raise HTTPException(status_code=401, detail="Invalid skill secret")


async def _send_error_callback(callback_url: str, kakao_user_id: str, message: str):
    """에러 응답을 콜백 URL로 전송"""
    try:
        error_response = KakaoResponse.text(message)
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(callback_url, json=error_response.model_dump(exclude_none=True))
    except Exception:
        logger.error("에러 콜백 전송 실패: user=%s", kakao_user_id)


async def _process_and_callback(
    callback_url: str, kakao_user_id: str, utterance: str
):
    """비동기 처리 후 콜백 URL로 응답 전송 (독립 DB 세션 사용, 25초 타임아웃)"""
    try:
        db = await get_new_session()
    except Exception as e:
        logger.error("DB 세션 생성 실패: %s, user=%s", e, kakao_user_id)
        await _send_error_callback(callback_url, kakao_user_id, "죄송해요, 일시적인 오류가 발생했어요. 다시 시도해주세요.")
        return

    try:
        async with db:
            response_text = await asyncio.wait_for(
                handle_utterance(db, kakao_user_id, utterance),
                timeout=25.0,
            )
            kakao_response = KakaoResponse.text(response_text)

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(callback_url, json=kakao_response.model_dump(exclude_none=True))
                logger.info("콜백 전송 완료: status=%d, user=%s", resp.status_code, kakao_user_id)

    except asyncio.TimeoutError:
        logger.error("백그라운드 처리 타임아웃(25초): user=%s", kakao_user_id)
        await _send_error_callback(callback_url, kakao_user_id, "처리 시간이 초과됐어요. 잠시 후 다시 시도해주세요.")
    except Exception as e:
        logger.error("콜백 처리 실패: type=%s, detail=%s, user=%s", type(e).__name__, e, kakao_user_id)
        await _send_error_callback(callback_url, kakao_user_id, "죄송해요, 처리 중 오류가 발생했어요. 다시 시도해주세요.")


@router.post("/skill", dependencies=[Depends(verify_kakao_skill_secret)])
async def kakao_skill(
    request: KakaoRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """카카오 챗봇 스킬 엔드포인트

    콜백 URL이 있으면: 즉시 대기 메시지 반환 + 비동기 처리
    콜백 URL이 없으면: 직접 응답 (5초 제한 내)
    """
    utterance = request.userRequest.utterance
    kakao_user_id = request.userRequest.params.get("plusfriendUserKey", "")

    kakao_user_id = kakao_user_id.strip()
    if not kakao_user_id or len(kakao_user_id) > 100:
        return KakaoResponse.text("사용자 인증에 실패했어요. 다시 시도해주세요.").model_dump(exclude_none=True)

    if not utterance.strip():
        return KakaoResponse.text("말씀해주세요! 매물 등록이나 검색을 도와드릴게요.").model_dump(exclude_none=True)

    # Rate limit 체크
    if _is_rate_limited(kakao_user_id):
        logger.warning("Rate limit 초과: user=%s", kakao_user_id)
        return KakaoResponse.text("요청이 너무 빨라요. 잠시 후 다시 시도해주세요.").model_dump(exclude_none=True)

    logger.info("스킬 요청: user=%s, utterance=%s", kakao_user_id, utterance[:50])

    if request.callbackUrl:
        background_tasks.add_task(
            _process_and_callback,
            request.callbackUrl, kakao_user_id, utterance,
        )
        return KakaoResponse.callback_pending(utterance).model_dump(exclude_none=True)

    response_text = await handle_utterance(db, kakao_user_id, utterance)
    return KakaoResponse.text(response_text).model_dump(exclude_none=True)
