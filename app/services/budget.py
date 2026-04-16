import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.budget import Budget
from app.models.category import Category
from app.models.user import User
from app.schemas.budget import BudgetCreate, BudgetUpdate


class BudgetService:

    @staticmethod
    async def _validate_category(category_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> None:
        result = await db.execute(
            select(Category).filter(
                Category.id == category_id,
                (Category.user_id == user_id) | (Category.is_system == True),
            )
        )
        if not result.scalar_one_or_none():
            raise NotFoundException("Category not found")

    @staticmethod
    async def create(payload: BudgetCreate, current_user: User, db: AsyncSession) -> Budget:
        if payload.category_id:
            await BudgetService._validate_category(payload.category_id, current_user.id, db)

        budget = Budget(
            user_id=current_user.id,
            category_id=payload.category_id,
            name=payload.name,
            amount=payload.amount,
            period=payload.period,
            start_date=payload.start_date,
            end_date=payload.end_date,
        )
        db.add(budget)
        await db.commit()
        await db.refresh(budget)
        return budget

    @staticmethod
    async def get_all(current_user: User, db: AsyncSession) -> list[Budget]:
        result = await db.execute(
            select(Budget)
            .filter(Budget.user_id == current_user.id)
            .order_by(Budget.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(budget_id: uuid.UUID, current_user: User, db: AsyncSession) -> Budget:
        result = await db.execute(
            select(Budget)
            .filter(Budget.id == budget_id, Budget.user_id == current_user.id)
        )
        budget = result.scalar_one_or_none()
        if not budget:
            raise NotFoundException("Budget not found")
        return budget

    @staticmethod
    async def update(budget_id: uuid.UUID, payload: BudgetUpdate, current_user: User, db: AsyncSession) -> Budget:
        budget = await BudgetService.get_by_id(budget_id, current_user, db)

        if payload.category_id is not None:
            await BudgetService._validate_category(payload.category_id, current_user.id, db)

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(budget, field, value)

        await db.commit()
        await db.refresh(budget)
        return budget

    @staticmethod
    async def delete(budget_id: uuid.UUID, current_user: User, db: AsyncSession) -> None:
        budget = await BudgetService.get_by_id(budget_id, current_user, db)
        await db.delete(budget)
        await db.commit()
