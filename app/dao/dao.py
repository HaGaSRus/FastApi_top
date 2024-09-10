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

    async def get_user_with_roles(self, user_id: int) -> Optional[UserResponse]:
        async with async_session_maker() as session:
            # Получение пользователя с ролями
            result = await session.execute(
                select(Users).options(joinedload(Users.roles)).where(Users.id == user_id)
            )
            user = result.unique().scalar_one_or_none()
            role = []
            if user:
                # Преобразование ролей в список объектов, соответствующих модели Role
                roles_data = [{"name": role.name} for role in user.roles]  # Создаем список словарей для ролей

                for value in roles_data:
                     role.append(value['name'])

                # value['name']

                # keys= roles_data.values()
                # print(keys)


                user_data: Dict[str, Any] = {
                    "username": user.username,
                    "email": user.email,
                    "roles": role  # Передаем преобразованные данные ролей
                }
                return UserResponse(**user_data)  # Создаем экземпляр UserResponse

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

    async def clear_roles(self, user_id: int):
        """Удаляет все роли пользователя."""
        async with async_session_maker() as session:
            # Удаляем все записи для данного пользователя из таблицы ассоциаций
            await session.execute(
                delete(role_user_association).where(
                    role_user_association.c.user_id == user_id
                )
            )
            await session.commit()

    async def add_roles(self, user_id: int, role_names: List[str]):
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
