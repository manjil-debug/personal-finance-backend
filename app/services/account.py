from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.user import User
from app.schemas.account import AccountCreate


def create_account(payload: AccountCreate, current_user: User, db: Session) -> Account:
    account = Account(
        user_id=current_user.id,
        name=payload.name,
        type=payload.type,
        balance=payload.balance,
        currency=payload.currency.upper(),
        color=payload.color,
        icon=payload.icon,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def get_user_accounts(current_user: User, db: Session) -> list[Account]:
    return (
        db.query(Account)
        .filter(Account.user_id == current_user.id, Account.is_active == True)
        .order_by(Account.created_at)
        .all()
    )


def get_account(account_id: str, current_user: User, db: Session) -> Account:
    account = (
        db.query(Account)
        .filter(Account.id == account_id, Account.user_id == current_user.id)
        .first()
    )
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account
