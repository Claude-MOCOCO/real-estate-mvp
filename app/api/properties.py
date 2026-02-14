"""내부 매물 CRUD API (개발/디버깅용)"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.property import (
    PropertyCreate,
    PropertyResponse,
    PropertyUpdate,
)
from app.services.property_service import (
    create_property,
    delete_property,
    get_property,
    list_properties,
    update_property,
)

router = APIRouter(prefix="/api/properties", tags=["properties"])


@router.get("/{agent_id}", response_model=list[PropertyResponse])
async def get_properties(
    agent_id: uuid.UUID,
    transaction_type: str | None = None,
    address_gugun: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await list_properties(db, agent_id, transaction_type, address_gugun, limit=limit, offset=offset)


@router.post("/{agent_id}", response_model=PropertyResponse, status_code=201)
async def create_property_endpoint(
    agent_id: uuid.UUID,
    data: PropertyCreate,
    db: AsyncSession = Depends(get_db),
):
    return await create_property(db, agent_id, data)


@router.get("/{agent_id}/{property_id}", response_model=PropertyResponse)
async def get_property_endpoint(
    agent_id: uuid.UUID,
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    prop = await get_property(db, agent_id, property_id)
    if prop is None:
        raise HTTPException(status_code=404, detail="매물을 찾을 수 없습니다")
    return prop


@router.patch("/{agent_id}/{property_id}", response_model=PropertyResponse)
async def update_property_endpoint(
    agent_id: uuid.UUID,
    property_id: uuid.UUID,
    data: PropertyUpdate,
    db: AsyncSession = Depends(get_db),
):
    prop = await update_property(db, agent_id, property_id, data)
    if prop is None:
        raise HTTPException(status_code=404, detail="매물을 찾을 수 없습니다")
    return prop


@router.delete("/{agent_id}/{property_id}", status_code=204)
async def delete_property_endpoint(
    agent_id: uuid.UUID,
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    success = await delete_property(db, agent_id, property_id)
    if not success:
        raise HTTPException(status_code=404, detail="매물을 찾을 수 없습니다")
