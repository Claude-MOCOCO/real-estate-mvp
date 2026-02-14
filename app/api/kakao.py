"""카카오 챗봇 스킬 서버 엔드포인트"""

import logging

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_new_session
from app.schemas.kakao import KakaoRequest, KakaoResponse
from app.services.assistant import handle_utterance

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/kakao", tags=["kakao"])


async def _process_and_callback(
    callback_url: str, kakao_user_id: str, utterance: str
):
    """비동기 처리 후 콜백 URL로 응답 전송 (독립 DB 세션 사용)"""
    db = await get_new_session()
    try:
        async with db:
            response_text = await handle_utterance(db, kakao_user_id, utterance)
            kakao_response = KakaoResponse.text(response_text)

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(callback_url, json=kakao_response.model_dump(exclude_none=True))
                logger.info("콜백 전송 완료: status=%d, user=%s", resp.status_code, kakao_user_id)

    except Exception as e:
        logger.error("콜백 처리 실패: %s, user=%s", e, kakao_user_id)
        try:
            error_response = KakaoResponse.text("죄송해요, 처리 중 오류가 발생했어요. 다시 시도해주세요.")
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(callback_url, json=error_response.model_dump(exclude_none=True))
        except Exception:
            logger.error("에러 콜백도 실패: user=%s", kakao_user_id)


@router.post("/skill")
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
    kakao_user_id = request.userRequest.params.get("plusfriendUserKey", "unknown")

    if not utterance.strip():
        return KakaoResponse.text("말씀해주세요! 매물 등록이나 검색을 도와드릴게요.").model_dump(exclude_none=True)

    logger.info("스킬 요청: user=%s, utterance=%s", kakao_user_id, utterance[:50])

    if request.callbackUrl:
        background_tasks.add_task(
            _process_and_callback,
            request.callbackUrl, kakao_user_id, utterance,
        )
        return KakaoResponse.callback_pending().model_dump(exclude_none=True)

    response_text = await handle_utterance(db, kakao_user_id, utterance)
    return KakaoResponse.text(response_text).model_dump(exclude_none=True)
