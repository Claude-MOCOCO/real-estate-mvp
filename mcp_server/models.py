"""Pydantic 모델 (검증, 변환)"""

from pydantic import BaseModel, field_validator
from typing import Optional


# ENUM 값 상수
PROPERTY_TYPES = ["아파트", "빌라", "오피스텔", "원룸", "상가", "사무실", "토지", "주택"]
TRADE_TYPES = ["매매", "전세", "월세"]
DIRECTIONS = ["남향", "남동향", "남서향", "동향", "서향", "북향", "북동향", "북서향"]
STATUSES = ["active", "in_contract", "completed", "hidden"]
SORT_OPTIONS = ["newest", "price_asc", "price_desc", "area_asc", "area_desc"]
PERIODS = ["this_month", "last_month", "this_year"]


class SearchParams(BaseModel):
    """매물 검색 파라미터"""
    region: str = ""
    property_type: Optional[str] = None
    trade_type: Optional[str] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    min_area: Optional[float] = None
    max_area: Optional[float] = None
    status: str = "active"
    sort_by: str = "newest"
    page: int = 1
    page_size: int = 10

    @field_validator("property_type")
    @classmethod
    def validate_property_type(cls, v):
        if v is not None and v not in PROPERTY_TYPES:
            raise ValueError(f"유효하지 않은 매물 유형: {v}. 가능한 값: {PROPERTY_TYPES}")
        return v

    @field_validator("trade_type")
    @classmethod
    def validate_trade_type(cls, v):
        if v is not None and v not in TRADE_TYPES:
            raise ValueError(f"유효하지 않은 거래 유형: {v}. 가능한 값: {TRADE_TYPES}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in STATUSES:
            raise ValueError(f"유효하지 않은 상태: {v}. 가능한 값: {STATUSES}")
        return v

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v):
        if v not in SORT_OPTIONS:
            raise ValueError(f"유효하지 않은 정렬 옵션: {v}. 가능한 값: {SORT_OPTIONS}")
        return v

    @field_validator("page")
    @classmethod
    def validate_page(cls, v):
        if v < 1:
            raise ValueError("page는 1 이상이어야 합니다.")
        return v

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, v):
        if v < 1 or v > 50:
            raise ValueError("page_size는 1~50 사이여야 합니다.")
        return v


class PropertyCreate(BaseModel):
    """매물 등록 파라미터"""
    property_type: str
    trade_type: str
    sido: str
    sigungu: str
    dong: str
    area_exclusive_m2: float
    sale_price: Optional[int] = None
    deposit: Optional[int] = None
    monthly_rent: Optional[int] = None
    address_detail: Optional[str] = None
    road_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    area_supply_m2: Optional[float] = None
    floor: Optional[str] = None
    total_floors: Optional[int] = None
    room_count: Optional[int] = None
    bathroom_count: Optional[int] = None
    direction: Optional[str] = None
    built_year: Optional[int] = None
    parking_available: Optional[bool] = None
    maintenance_fee: Optional[int] = None
    options: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    memo: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None

    @field_validator("property_type")
    @classmethod
    def validate_property_type(cls, v):
        if v not in PROPERTY_TYPES:
            raise ValueError(f"유효하지 않은 매물 유형: {v}. 가능한 값: {PROPERTY_TYPES}")
        return v

    @field_validator("trade_type")
    @classmethod
    def validate_trade_type(cls, v):
        if v not in TRADE_TYPES:
            raise ValueError(f"유효하지 않은 거래 유형: {v}. 가능한 값: {TRADE_TYPES}")
        return v

    @field_validator("area_exclusive_m2")
    @classmethod
    def validate_area(cls, v):
        if v <= 0:
            raise ValueError("전용면적은 0보다 커야 합니다.")
        return v

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v):
        if v is not None and v not in DIRECTIONS:
            raise ValueError(f"유효하지 않은 방향: {v}. 가능한 값: {DIRECTIONS}")
        return v

    @field_validator("built_year")
    @classmethod
    def validate_built_year(cls, v):
        if v is not None and (v < 1900 or v > 2100):
            raise ValueError("준공년도는 1900~2100 사이여야 합니다.")
        return v


class PropertyUpdate(BaseModel):
    """매물 수정 파라미터 (수정할 필드만 전달)"""
    property_type: Optional[str] = None
    trade_type: Optional[str] = None
    sido: Optional[str] = None
    sigungu: Optional[str] = None
    dong: Optional[str] = None
    address_detail: Optional[str] = None
    road_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    area_exclusive_m2: Optional[float] = None
    area_supply_m2: Optional[float] = None
    sale_price: Optional[int] = None
    deposit: Optional[int] = None
    monthly_rent: Optional[int] = None
    floor: Optional[str] = None
    total_floors: Optional[int] = None
    room_count: Optional[int] = None
    bathroom_count: Optional[int] = None
    direction: Optional[str] = None
    built_year: Optional[int] = None
    parking_available: Optional[bool] = None
    maintenance_fee: Optional[int] = None
    options: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    memo: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
