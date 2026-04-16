from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserUpdate


class UserService:

    @staticmethod
    async def get_profile(current_user: User) -> User:
        return current_user

    @staticmethod
    async def update_profile(payload: UserUpdate, current_user: User, db: AsyncSession) -> User:
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(current_user, field, value)

        await db.commit()
        await db.refresh(current_user)
        return current_user
