import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.value_objects import (
    MemoCreate,
    ParseResult,
    PropertyStatus,
    TransactionType,
)


class PropertyCreate(BaseModel):
    transaction_type: TransactionType | None = None
    price_main: int | None = Field(None, ge=0)
    price_monthly: int | None = Field(None, ge=0)
    area_pyeong: float | None = Field(None, gt=0)
    address_sido: str | None = Field(None, max_length=20)
    address_gugun: str | None = Field(None, max_length=20)
    address_dong: str | None = Field(None, max_length=30)
    building_name: str | None = Field(None, max_length=50)
    extra: dict = Field(default_factory=dict)
    raw_input: str | None = Field(None, max_length=1000)


class PropertyUpdate(BaseModel):
    transaction_type: TransactionType | None = None
    price_main: int | None = Field(None, ge=0)
    price_monthly: int | None = Field(None, ge=0)
    area_pyeong: float | None = Field(None, gt=0)
    address_sido: str | None = Field(None, max_length=20)
    address_gugun: str | None = Field(None, max_length=20)
    address_dong: str | None = Field(None, max_length=30)
    building_name: str | None = Field(None, max_length=50)
    extra: dict | None = None


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


class MemoResponse(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    content: str
    resolved: bool
    created_at: datetime

    model_config = {"from_attributes": True}
