from sqlalchemy import insert
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.dao.base import BaseDAO
from app.database import async_session_maker
from app.users.models import Users, Roles, Permissions, role_user_association


class UsersDAO(BaseDAO):
    model = Users

    async def add(self, username: str, firstname: str, lastname: str, email: str, hashed_password: str):
        async with async_session_maker() as session:
            # Создание нового пользователя
            new_user = Users(
                username=username,
                firstname=firstname,
                lastname=lastname,
                email=email,
                hashed_password=hashed_password
            )
            session.add(new_user)
            await session.commit()
            return new_user

    async def get_user_with_roles(self, user_id: int):
        async with async_session_maker() as session:
            # Получение пользователя с ролями
            result = await session.execute(
                select(Users).options(joinedload(Users.roles)).where(Users.id == user_id)
            )
            user = result.unique().scalar_one_or_none()

            # Если пользователь найден, преобразуем в формат, соответствующий модели UserResponse
            if user:
                user_dict = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "firstname": user.firstname,
                    "lastname": user.lastname,
                    "roles": [role.__dict__ for role in user.roles]  # Преобразуем роли в словари
                }
                return user_dict

            return None

    @classmethod
    async def get_user_by_email(cls, email: str):
        async with async_session_maker() as session:
            query = select(cls.model).filter_by(email=email)
            result = await session.execute(query)
            return result.scalar_one_or_none()

class UsersRolesDAO(BaseDAO):
    model = Roles

    async def add(self, user_id: int, role_name: str):
        async with async_session_maker() as session:
            # Получение роли по имени
            role = await session.execute(
                select(Roles).where(Roles.name == role_name)
            )
            role = role.scalar_one_or_none()

            if not role:
                raise ValueError("Роль не найдена")

            # Вставка в таблицу ассоциаций
            stmt = insert(role_user_association).values(user_id=user_id, role_id=role.id)
            await session.execute(stmt)
            await session.commit()

class UserPermissionsDAO(BaseDAO):
    model = Permissions
