import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, UnprocessableException
from app.models.account import Account
from app.models.transaction import Transaction, TransactionType
from app.models.transfer import Transfer
from app.models.user import User
from app.schemas.transfer import TransferCreate, TransferResponse, TransferUpdate


class TransferService:

    @staticmethod
    async def _get_active_account(account_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> Account:
        result = await db.execute(
            select(Account)
            .filter(Account.id == account_id, Account.user_id == user_id, Account.is_active == True)
        )
        account = result.scalar_one_or_none()
        if not account:
            raise NotFoundException("Account not found")
        return account

    @staticmethod
    async def _build_response(transfer: Transfer, from_txn: Transaction, to_txn: Transaction) -> TransferResponse:
        return TransferResponse(
            id=transfer.id,
            user_id=transfer.user_id,
            from_transaction_id=transfer.from_transaction_id,
            to_transaction_id=transfer.to_transaction_id,
            from_account_id=from_txn.account_id,
            to_account_id=to_txn.account_id,
            amount=from_txn.amount,
            currency=from_txn.currency,
            description=from_txn.description,
            date=from_txn.date,
            created_at=transfer.created_at,
        )

    @staticmethod
    async def create(payload: TransferCreate, current_user: User, db: AsyncSession) -> TransferResponse:
        from_account = await TransferService._get_active_account(payload.from_account_id, current_user.id, db)
        to_account = await TransferService._get_active_account(payload.to_account_id, current_user.id, db)

        if from_account.balance < payload.amount:
            raise UnprocessableException("Insufficient balance in source account")

        description = payload.description or f"Transfer from {from_account.name} to {to_account.name}"

        from_txn = Transaction(
            user_id=current_user.id,
            account_id=payload.from_account_id,
            type=TransactionType.transfer,
            amount=payload.amount,
            currency=payload.currency.upper(),
            description=description,
            notes=payload.notes,
            date=payload.date,
        )
        to_txn = Transaction(
            user_id=current_user.id,
            account_id=payload.to_account_id,
            type=TransactionType.transfer,
            amount=payload.amount,
            currency=payload.currency.upper(),
            description=description,
            notes=payload.notes,
            date=payload.date,
        )

        db.add(from_txn)
        db.add(to_txn)
        await db.flush()

        from_account.balance -= payload.amount
        to_account.balance += payload.amount

        transfer = Transfer(
            user_id=current_user.id,
            from_transaction_id=from_txn.id,
            to_transaction_id=to_txn.id,
        )
        db.add(transfer)
        await db.commit()
        await db.refresh(transfer)
        await db.refresh(from_txn)
        await db.refresh(to_txn)

        return await TransferService._build_response(transfer, from_txn, to_txn)

    @staticmethod
    async def get_all(current_user: User, db: AsyncSession) -> list[TransferResponse]:
        result = await db.execute(
            select(Transfer)
            .filter(Transfer.user_id == current_user.id)
            .order_by(Transfer.created_at.desc())
        )
        transfers = result.scalars().all()

        results: list[TransferResponse] = []
        for t in transfers:
            from_result = await db.execute(select(Transaction).filter(Transaction.id == t.from_transaction_id))
            to_result = await db.execute(select(Transaction).filter(Transaction.id == t.to_transaction_id))
            from_txn = from_result.scalar_one_or_none()
            to_txn = to_result.scalar_one_or_none()
            if not from_txn or not to_txn:
                continue
            results.append(await TransferService._build_response(t, from_txn, to_txn))
        return results

    @staticmethod
    async def get_by_id(transfer_id: uuid.UUID, current_user: User, db: AsyncSession) -> TransferResponse:
        result = await db.execute(
            select(Transfer)
            .filter(Transfer.id == transfer_id, Transfer.user_id == current_user.id)
        )
        transfer = result.scalar_one_or_none()
        if not transfer:
            raise NotFoundException("Transfer not found")

        from_result = await db.execute(select(Transaction).filter(Transaction.id == transfer.from_transaction_id))
        to_result = await db.execute(select(Transaction).filter(Transaction.id == transfer.to_transaction_id))
        from_txn = from_result.scalar_one_or_none()
        to_txn = to_result.scalar_one_or_none()
        if not from_txn or not to_txn:
            raise NotFoundException("Transfer transactions not found")

        return await TransferService._build_response(transfer, from_txn, to_txn)

    @staticmethod
    async def delete(transfer_id: uuid.UUID, current_user: User, db: AsyncSession) -> None:
        result = await db.execute(
            select(Transfer)
            .filter(Transfer.id == transfer_id, Transfer.user_id == current_user.id)
        )
        transfer = result.scalar_one_or_none()
        if not transfer:
            raise NotFoundException("Transfer not found")

        from_result = await db.execute(select(Transaction).filter(Transaction.id == transfer.from_transaction_id))
        to_result = await db.execute(select(Transaction).filter(Transaction.id == transfer.to_transaction_id))
        from_txn = from_result.scalar_one_or_none()
        to_txn = to_result.scalar_one_or_none()

        if from_txn:
            acc_result = await db.execute(select(Account).filter(Account.id == from_txn.account_id))
            from_account = acc_result.scalar_one_or_none()
            if from_account:
                from_account.balance += from_txn.amount

        if to_txn:
            acc_result = await db.execute(select(Account).filter(Account.id == to_txn.account_id))
            to_account = acc_result.scalar_one_or_none()
            if to_account:
                to_account.balance -= to_txn.amount

        await db.delete(transfer)
        if from_txn:
            await db.delete(from_txn)
        if to_txn:
            await db.delete(to_txn)

        await db.commit()

    @staticmethod
    async def update(
        transfer_id: uuid.UUID, payload: TransferUpdate, current_user: User, db: AsyncSession
    ) -> TransferResponse:
        result = await db.execute(
            select(Transfer)
            .filter(Transfer.id == transfer_id, Transfer.user_id == current_user.id)
        )
        transfer = result.scalar_one_or_none()
        if not transfer:
            raise NotFoundException("Transfer not found")

        from_result = await db.execute(select(Transaction).filter(Transaction.id == transfer.from_transaction_id))
        to_result = await db.execute(select(Transaction).filter(Transaction.id == transfer.to_transaction_id))
        from_txn = from_result.scalar_one_or_none()
        to_txn = to_result.scalar_one_or_none()
        if not from_txn or not to_txn:
            raise NotFoundException("Transfer transactions not found")

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(from_txn, field, value)
            setattr(to_txn, field, value)

        await db.commit()
        await db.refresh(transfer)
        await db.refresh(from_txn)
        await db.refresh(to_txn)

        return await TransferService._build_response(transfer, from_txn, to_txn)
