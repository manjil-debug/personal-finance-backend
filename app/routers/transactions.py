import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.transaction import TransactionCreate, TransactionResponse
from app.services.transaction import create_transaction, get_transaction, get_user_transactions

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def add_transaction(
    payload: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_transaction(payload, current_user, db)


@router.get("", response_model=list[TransactionResponse])
def list_transactions(
    account_id: Optional[uuid.UUID] = Query(default=None, description="Filter by account"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_user_transactions(current_user, db, account_id)


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_single_transaction(
    transaction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_transaction(transaction_id, current_user, db)
