from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.user import User


class CategoryService:

    @staticmethod
    async def get_all(current_user: User, db: AsyncSession) -> list[Category]:
        result = await db.execute(
            select(Category)
            .filter(
                (Category.user_id == current_user.id) | (Category.is_system == True)
            )
            .order_by(Category.name)
        )
        return list(result.scalars().all())
