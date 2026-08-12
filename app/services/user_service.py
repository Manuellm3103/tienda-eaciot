"""User helpers, including guest checkout account creation."""
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User


class UserService:
    async def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create_guest_user(
        self, db: AsyncSession, email: str, name: Optional[str] = None
    ) -> User:
        """Create a guest user for checkout without a password."""
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            hashed_password="",
            is_guest=True,
        )
        db.add(user)
        await db.flush()
        return user


user_service = UserService()
