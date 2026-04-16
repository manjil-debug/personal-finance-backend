import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.account import Account
from app.models.user import User
from app.schemas.account import AccountCreate, AccountUpdate


class AccountService:

    @staticmethod
    async def create(payload: AccountCreate, current_user: User, db: AsyncSession) -> Account:
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
        await db.commit()
        await db.refresh(account)
        return account

    @staticmethod
    async def get_all(current_user: User, db: AsyncSession) -> list[Account]:
        result = await db.execute(
            select(Account)
            .filter(Account.user_id == current_user.id, Account.is_active == True)
            .order_by(Account.created_at)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(account_id: uuid.UUID, current_user: User, db: AsyncSession) -> Account:
        result = await db.execute(
            select(Account)
            .filter(Account.id == account_id, Account.user_id == current_user.id)
        )
        account = result.scalar_one_or_none()
        if not account:
            raise NotFoundException("Account not found")
        return account

    @staticmethod
    async def update(account_id: uuid.UUID, payload: AccountUpdate, current_user: User, db: AsyncSession) -> Account:
        account = await AccountService.get_by_id(account_id, current_user, db)
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(account, field, value)
        await db.commit()
        await db.refresh(account)
        return account

    @staticmethod
    async def deactivate(account_id: uuid.UUID, current_user: User, db: AsyncSession) -> None:
        account = await AccountService.get_by_id(account_id, current_user, db)
        account.is_active = False
        await db.commit()
