import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.transfer import TransferCreate, TransferResponse, TransferUpdate
from app.services.transfer import TransferService

router = APIRouter(prefix="/transfers", tags=["Transfers"])


@router.post("", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
async def add_transfer(
    payload: TransferCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await TransferService.create(payload, current_user, db)


@router.get("", response_model=list[TransferResponse])
async def list_transfers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await TransferService.get_all(current_user, db)


@router.get("/{transfer_id}", response_model=TransferResponse)
async def get_single_transfer(
    transfer_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await TransferService.get_by_id(transfer_id, current_user, db)


@router.put("/{transfer_id}", response_model=TransferResponse)
async def update_transfer(
    transfer_id: uuid.UUID,
    payload: TransferUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await TransferService.update(transfer_id, payload, current_user, db)


@router.delete("/{transfer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_transfer(
    transfer_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await TransferService.delete(transfer_id, current_user, db)
