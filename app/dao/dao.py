from typing import Dict, Any, Optional, List

from sqlalchemy import insert, delete
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.dao.base import BaseDAO
from app.database import async_session_maker
from app.logger.logger import logger
from app.users.models import Users, Roles, Permissions, role_user_association
from app.users.schemas import UserResponse


class UsersDAO(BaseDAO):
    model = Users

    @classmethod
    async def add(cls, username: str, firstname: str, lastname: str, email: str, hashed_password: str):
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

    @classmethod
    async def get_user_with_roles(cls, user_id: int) -> Optional[UserResponse]:
        async with async_session_maker() as session:
            result = await session.execute(
                select(Users).options(joinedload(Users.roles)).where(Users.id == user_id)
            )
            user = result.unique().scalar_one_or_none()

            if user:
                roles = [role.name for role in user.roles]  # Прямое преобразование в список строк
                user_data: Dict[str, Any] = {
                    "username": user.username,
                    "email": user.email,
                    "roles": roles
                }
                return UserResponse(**user_data)

            return None

    @classmethod
    async def get_user_by_email(cls, email: str):
        async with async_session_maker() as session:
            query = select(cls.model).filter_by(email=email)
            result = await session.execute(query)
            return result.scalar_one_or_none()

class UsersRolesDAO(BaseDAO):
    model = Roles

    @classmethod
    async def add(cls, user_id: int, role_name: str):
        async with async_session_maker() as session:
            # Получение роли по имени
            role = await session.execute(
                select(Roles).where(Roles.name == role_name)
            )
            role = role.scalar_one_or_none()

            if not role:
                raise ValueError("Роль не найдена")

            # Проверяем, есть ли уже эта роль у пользователя
            existing_association = await session.execute(
                select(role_user_association).where(
                    role_user_association.c.user_id == user_id,
                    role_user_association.c.role_id == role.id
                )
            )
            if existing_association.fetchone():
                logger.info(f"Пользователь уже имеет роль {role_name}")
                return  # Прекращаем выполнение, если роль уже есть

            # Вставка в таблицу ассоциаций
            stmt = insert(role_user_association).values(user_id=user_id, role_id=role.id)
            await session.execute(stmt)
            await session.commit()

    @classmethod
    async def clear_roles(cls, user_id: int):
        """Удаляет все роли пользователя."""
        async with async_session_maker() as session:
            # Удаляем все записи для данного пользователя из таблицы ассоциаций
            await session.execute(
                delete(role_user_association).where(
                    role_user_association.c.user_id == user_id
                )
            )
            await session.commit()

    @classmethod
    async def add_roles(cls, user_id: int, role_names: List[str]):
        """Добавляет указанные роли пользователю."""
        async with async_session_maker() as session:
            for role_name in role_names:
                # Получаем роль по имени
                role = await session.execute(
                    select(Roles).where(Roles.name == role_name)
                )
                role = role.scalar_one_or_none()

                if not role:
                    logger.error(f"Роль {role_name} не найдена")
                    continue

                # Проверяем, есть ли уже эта роль у пользователя
                existing_association = await session.execute(
                    select(role_user_association).where(
                        role_user_association.c.user_id == user_id,
                        role_user_association.c.role_id == role.id
                    )
                )
                if existing_association.fetchone():
                    logger.info(f"Пользователь уже имеет роль {role_name}")
                    continue  # Пропускаем, если роль уже есть

                # Вставка в таблицу ассоциаций
                stmt = insert(role_user_association).values(user_id=user_id, role_id=role.id)
                await session.execute(stmt)

            await session.commit()

class UserPermissionsDAO(BaseDAO):
    model = Permissions
