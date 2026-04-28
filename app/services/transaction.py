import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException, UnprocessableException
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction, TransactionType
from app.models.user import User
from app.schemas.transaction import TransactionCreate, TransactionUpdate


class TransactionService:

    @staticmethod
    async def _get_account_for_user(account_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> Account:
        result = await db.execute(
            select(Account)
            .filter(Account.id == account_id, Account.user_id == user_id, Account.is_active == True)
        )
        account = result.scalar_one_or_none()
        if not account:
            raise NotFoundException("Account not found")
        return account

    @staticmethod
    async def _validate_category(category_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> None:
        result = await db.execute(
            select(Category)
            .filter(
                Category.id == category_id,
                (Category.user_id == user_id) | (Category.is_system == True),
            )
        )
        category = result.scalar_one_or_none()
        if not category:
            raise NotFoundException("Category not found")

    @staticmethod
    async def create(payload: TransactionCreate, current_user: User, db: AsyncSession) -> Transaction:
        account = await TransactionService._get_account_for_user(payload.account_id, current_user.id, db)

        if payload.category_id:
            await TransactionService._validate_category(payload.category_id, current_user.id, db)

        if payload.type == TransactionType.transfer:
            raise BadRequestException("Use the /transfers endpoint to create transfer transactions")

        if payload.type == TransactionType.income:
            account.balance += payload.amount
        elif payload.type == TransactionType.expense:
            if account.balance - payload.amount < 0:
                raise UnprocessableException("Insufficient balance for this transaction")
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
        await db.commit()
        await db.refresh(transaction)
        return transaction

    @staticmethod
    async def get_all(
        current_user: User,
        db: AsyncSession,
        account_id: Optional[uuid.UUID] = None,
    ) -> list[Transaction]:
        stmt = select(Transaction).filter(Transaction.user_id == current_user.id)
        if account_id:
            stmt = stmt.filter(Transaction.account_id == account_id)
        stmt = stmt.order_by(Transaction.date.desc(), Transaction.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def delete(transaction_id: uuid.UUID, current_user: User, db: AsyncSession) -> None:
        result = await db.execute(
            select(Transaction)
            .filter(Transaction.id == transaction_id, Transaction.user_id == current_user.id)
        )
        transaction = result.scalar_one_or_none()
        if not transaction:
            raise NotFoundException("Transaction not found")

        if transaction.type == TransactionType.transfer:
            raise BadRequestException("Transfer transactions cannot be deleted directly. Use the /transfers endpoint instead.")

        result = await db.execute(
            select(Account).filter(Account.id == transaction.account_id)
        )
        account = result.scalar_one_or_none()
        if account:
            if transaction.type == TransactionType.income:
                account.balance -= transaction.amount
            elif transaction.type == TransactionType.expense:
                account.balance += transaction.amount

        await db.delete(transaction)
        await db.commit()

    @staticmethod
    async def get_by_id(transaction_id: uuid.UUID, current_user: User, db: AsyncSession) -> Transaction:
        result = await db.execute(
            select(Transaction)
            .filter(Transaction.id == transaction_id, Transaction.user_id == current_user.id)
        )
        transaction = result.scalar_one_or_none()
        if not transaction:
            raise NotFoundException("Transaction not found")
        return transaction

    @staticmethod
    async def update(
        transaction_id: uuid.UUID, payload: TransactionUpdate, current_user: User, db: AsyncSession
    ) -> Transaction:
        transaction = await TransactionService.get_by_id(transaction_id, current_user, db)

        if transaction.type == TransactionType.transfer:
            raise BadRequestException("Transfer transactions cannot be edited directly. Use the /transfers endpoint instead.")

        if payload.category_id is not None:
            await TransactionService._validate_category(payload.category_id, current_user.id, db)

        update_data = payload.model_dump(exclude_unset=True)

        new_type = update_data.get("type", None)
        if new_type == TransactionType.transfer:
            raise BadRequestException("Cannot change transaction type to transfer. Use the /transfers endpoint instead.")

        new_amount = update_data.get("amount", None)

        # Recalculate account balance if amount or type changed
        if new_amount is not None or new_type is not None:
            account = await TransactionService._get_account_for_user(
                transaction.account_id, current_user.id, db
            )

            # Reverse the old transaction effect
            if transaction.type == TransactionType.income:
                account.balance -= transaction.amount
            elif transaction.type == TransactionType.expense:
                account.balance += transaction.amount

            effective_type = new_type or transaction.type
            effective_amount = new_amount if new_amount is not None else transaction.amount

            # Apply the new transaction effect
            if effective_type == TransactionType.income:
                account.balance += effective_amount
            elif effective_type == TransactionType.expense:
                if account.balance - effective_amount < 0:
                    raise UnprocessableException("Insufficient balance for this transaction")
                account.balance -= effective_amount

        for field, value in update_data.items():
            setattr(transaction, field, value)

        await db.commit()
        await db.refresh(transaction)
        return transaction
