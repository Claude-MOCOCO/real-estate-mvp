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


class ParseResult(BaseModel):
    """AI 파싱 결과"""

    intent: Literal["register", "search", "update", "delete", "list_memo", "unknown"] = "unknown"
    transaction_type: str | None = None
    price_main: int | None = Field(None, ge=0, le=10**12)
    price_monthly: int | None = Field(None, ge=0, le=10**9)
    area_pyeong: float | None = Field(None, gt=0, le=10000)
    address_sido: str | None = Field(None, max_length=20)
    address_gugun: str | None = Field(None, max_length=20)
    address_dong: str | None = Field(None, max_length=30)
    building_name: str | None = Field(None, max_length=50)
    extra: dict = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    clarification_needed: str | None = None


class MemoCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
