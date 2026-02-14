import uuid
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class TransactionType(str, Enum):
    SALE = "매매"
    JEONSE = "전세"
    MONTHLY = "월세"


class PropertyStatus(str, Enum):
    ACTIVE = "active"
    SOLD = "sold"
    DELETED = "deleted"


class PropertyCreate(BaseModel):
    transaction_type: TransactionType | None = None
    price_main: int | None = Field(None, ge=0)
    price_monthly: int | None = Field(None, ge=0)
    area_pyeong: float | None = Field(None, gt=0)
    address_sido: str | None = None
    address_gugun: str | None = None
    address_dong: str | None = None
    building_name: str | None = None
    extra: dict = {}
    raw_input: str | None = None


class PropertyUpdate(BaseModel):
    transaction_type: TransactionType | None = None
    price_main: int | None = Field(None, ge=0)
    price_monthly: int | None = Field(None, ge=0)
    area_pyeong: float | None = Field(None, gt=0)
    address_sido: str | None = None
    address_gugun: str | None = None
    address_dong: str | None = None
    building_name: str | None = None
    extra: dict | None = None
    status: PropertyStatus | None = None


class PropertyResponse(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    transaction_type: str | None
    price_main: int | None
    price_monthly: int | None
    area_pyeong: float | None
    address_sido: str | None
    address_gugun: str | None
    address_dong: str | None
    building_name: str | None
    extra: dict
    raw_input: str | None
    status: PropertyStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ParseResult(BaseModel):
    """AI 파싱 결과"""

    intent: Literal["register", "search", "update", "delete", "list_memo", "unknown"] = "unknown"
    transaction_type: str | None = None
    price_main: int | None = None
    price_monthly: int | None = None
    area_pyeong: float | None = None
    address_sido: str | None = None
    address_gugun: str | None = None
    address_dong: str | None = None
    building_name: str | None = None
    extra: dict = {}
    missing_fields: list[str] = []
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    clarification_needed: str | None = None


class MemoCreate(BaseModel):
    content: str


class MemoResponse(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    content: str
    resolved: bool
    created_at: datetime

    model_config = {"from_attributes": True}
