"""카카오 스킬 API 엔드포인트 테스트"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")


def test_kakao_skill_direct_response(client):
    """콜백 URL 없는 직접 응답 모드"""
    with patch("app.api.kakao.handle_utterance", new_callable=AsyncMock) as mock:
        mock.return_value = "테스트 응답입니다"

        response = client.post(
            "/kakao/skill",
            json={
                "userRequest": {
                    "utterance": "역삼동 매물 뭐 있어?",
                    "params": {"plusfriendUserKey": "test_user_123"},
                },
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "2.0"
    assert data["template"]["outputs"][0]["simpleText"]["text"] == "테스트 응답입니다"


def test_kakao_skill_callback_mode(client):
    """콜백 URL 있는 비동기 처리 모드"""
    response = client.post(
        "/kakao/skill",
        json={
            "userRequest": {
                "utterance": "강남구 역삼동 30평 전세 3억 등록해줘",
                "params": {"plusfriendUserKey": "test_user_123"},
            },
            "callbackUrl": "https://callback.kakao.com/test",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["useCallback"] is True
    assert "잠시만요" in data["template"]["outputs"][0]["simpleText"]["text"]
