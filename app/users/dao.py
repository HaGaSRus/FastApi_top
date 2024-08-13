from app.dao.base import BaseDAO
from app.database import async_session_maker
from app.users.models import Users
from sqlalchemy.future import select


class UsersDAO(BaseDAO):
    model = Users

    @staticmethod
    async def find_by_email(email:  str):
        async with async_session_maker() as session:
            result = await session.execute(select(Users).where(Users.email == email))
            user = result.scalar_one_or_none()
        return user
