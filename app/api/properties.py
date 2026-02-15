"""내부 매물 CRUD API (개발/디버깅용)"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app.application.dependencies import get_property_use_case
from app.application.use_cases import PropertyUseCase
from app.core.auth import verify_api_key
from app.schemas.property import (
    PropertyCreate,
    PropertyResponse,
    PropertyUpdate,
)

router = APIRouter(
    prefix="/api/properties",
    tags=["properties"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/{agent_id}", response_model=list[PropertyResponse])
async def get_properties(
    agent_id: uuid.UUID,
    transaction_type: str | None = None,
    address_gugun: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    uc: PropertyUseCase = Depends(get_property_use_case),
):
    return await uc.list_properties(agent_id, transaction_type, address_gugun, limit=limit, offset=offset)


@router.post("/{agent_id}", response_model=PropertyResponse, status_code=201)
async def create_property_endpoint(
    agent_id: uuid.UUID,
    data: PropertyCreate,
    uc: PropertyUseCase = Depends(get_property_use_case),
):
    return await uc.create_property(agent_id, data)


@router.get("/{agent_id}/{property_id}", response_model=PropertyResponse)
async def get_property_endpoint(
    agent_id: uuid.UUID,
    property_id: uuid.UUID,
    uc: PropertyUseCase = Depends(get_property_use_case),
):
    prop = await uc.get_property(agent_id, property_id)
    if prop is None:
        raise HTTPException(status_code=404, detail="매물을 찾을 수 없습니다")
    return prop


@router.patch("/{agent_id}/{property_id}", response_model=PropertyResponse)
async def update_property_endpoint(
    agent_id: uuid.UUID,
    property_id: uuid.UUID,
    data: PropertyUpdate,
    uc: PropertyUseCase = Depends(get_property_use_case),
):
    prop = await uc.update_property(agent_id, property_id, data)
    if prop is None:
        raise HTTPException(status_code=404, detail="매물을 찾을 수 없습니다")
    return prop


@router.delete("/{agent_id}/{property_id}", status_code=204)
async def delete_property_endpoint(
    agent_id: uuid.UUID,
    property_id: uuid.UUID,
    uc: PropertyUseCase = Depends(get_property_use_case),
):
    success = await uc.delete_property(agent_id, property_id)
    if not success:
        raise HTTPException(status_code=404, detail="매물을 찾을 수 없습니다")
