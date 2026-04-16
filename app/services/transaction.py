import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction, TransactionType
from app.models.user import User
from app.schemas.transaction import TransactionCreate


def _get_account_for_user(account_id: uuid.UUID, user_id: uuid.UUID, db: Session) -> Account:
    account = (
        db.query(Account)
        .filter(Account.id == account_id, Account.user_id == user_id, Account.is_active == True)
        .first()
    )
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account


def _validate_category(category_id: uuid.UUID, user_id: uuid.UUID, db: Session) -> None:
    category = (
        db.query(Category)
        .filter(
            Category.id == category_id,
            (Category.user_id == user_id) | (Category.is_system == True),
        )
        .first()
    )
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")


def create_transaction(payload: TransactionCreate, current_user: User, db: Session) -> Transaction:
    account = _get_account_for_user(payload.account_id, current_user.id, db)

    if payload.category_id:
        _validate_category(payload.category_id, current_user.id, db)

    if payload.type == TransactionType.transfer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use the /transfers endpoint to create transfer transactions",
        )

    # Update account balance atomically within the same transaction
    if payload.type == TransactionType.income:
        account.balance += payload.amount
    elif payload.type == TransactionType.expense:
        if account.balance - payload.amount < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Insufficient balance for this transaction",
            )
        account.balance -= payload.amount

    transaction = Transaction(
        user_id=current_user.id,
        account_id=payload.account_id,
        category_id=payload.category_id,
        type=payload.type,
        amount=payload.amount,
        currency=payload.currency.upper(),
        description=payload.description,
        notes=payload.notes,
        date=payload.date,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def get_user_transactions(
    current_user: User,
    db: Session,
    account_id: Optional[uuid.UUID] = None,
) -> list[Transaction]:
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    return query.order_by(Transaction.date.desc(), Transaction.created_at.desc()).all()


def get_transaction(transaction_id: uuid.UUID, current_user: User, db: Session) -> Transaction:
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == current_user.id)
        .first()
    )
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return transaction
