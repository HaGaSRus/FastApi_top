from sqlalchemy import insert

from app.dao.base import BaseDAO
from app.database import async_session_maker
from app.users.models import Users, Roles, Permissions, role_user_association
from sqlalchemy.future import select


class UsersDAO(BaseDAO):
    model = Users


class UsersRolesDAO(BaseDAO):
    model = Roles

    async def add(user_id: int, role_name: str):
        async with async_session_maker() as session:
            # Получение роли по имени
            role = await session.execute(
                select(Roles).where(Roles.name == role_name)
            )
            role = role.scalar_one_or_none()

            if not role:
                raise ValueError("Role not found")

            # Вставка в таблицу ассоциаций
            stmt = insert(role_user_association).values(user_id=user_id, role_id=role.id)
            await session.execute(stmt)
            await session.commit()


class UserPermissionsDAO(BaseDAO):
    model = Permissions

