"""property_service 순수 함수 테스트"""

from app.services.property_service import _escape_like


def test_escape_like_percent():
    assert _escape_like("100%") == "100\\%"


def test_escape_like_underscore():
    assert _escape_like("a_b") == "a\\_b"


def test_escape_like_backslash():
    assert _escape_like("a\\b") == "a\\\\b"


def test_escape_like_combined():
    assert _escape_like("50%_test\\") == "50\\%\\_test\\\\"


def test_escape_like_no_special():
    assert _escape_like("강남구") == "강남구"
