from typing import Optional, List
from sqlalchemy import insert, delete
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.dao.base import BaseDAO
from app.database import async_session_maker
from app.logger.logger import logger
from app.questions.models import Question
from app.users.models import Users, Roles, Permissions, role_user_association
from app.users.schemas import UserResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession


class UsersDAO(BaseDAO):
    model = Users

    @classmethod
    async def add(cls, username: str, firstname: str, email: str, hashed_password: str):
        async with async_session_maker() as session:
            try:
                new_user = Users(
                    username=username,
                    firstname=firstname,
                    email=email,
                    hashed_password=hashed_password
                )
                session.add(new_user)
                await session.commit()
                logger.info(f"Новый пользователь добавлен: {username}")
                return new_user
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Ошибка при добавлении пользователя: {e}")
                raise

    @classmethod
    async def find_by_username_or_email(cls, username: Optional[str] = None, email: Optional[str] = None):
        async with async_session_maker() as session:
            try:
                query = select(cls.model)
                if username and email:
                    query = query.where(or_(cls.model.username == username, cls.model.email == email))
                elif username:
                    query = query.where(cls.model.username == username)
                elif email:
                    query = query.where(cls.model.email == email)
                result = await session.execute(query)
                user = result.scalar()
                logger.info(f"Пользователь найден: {user.username if user else 'не найден'}")
                return user
            except SQLAlchemyError as e:
                logger.error(f"Ошибка при поиске пользователя: {e}")
                raise

    @classmethod
    async def get_user_with_roles(cls, user_id: int) -> Optional[UserResponse]:
        async with async_session_maker() as session:
            try:
                result = await session.execute(
                    select(Users).options(selectinload(Users.roles)).where(Users.id == user_id)
                )
                user = result.scalar_one_or_none()

                if user:
                    user_data = UserResponse(
                        username=user.username,
                        email=user.email,
                        firstname=user.firstname,
                        roles=[role.name for role in user.roles]  # Преобразуем роли в список строк
                    )
                    logger.info(f"Пользователь с ролями получен: {user.username}")
                    return user_data

                logger.warning(f"Пользователь с id={user_id} не найден.")
                return None
            except SQLAlchemyError as e:
                logger.error(f"Ошибка при получении пользователя с ролями: {e}")
                raise

    @classmethod
    async def get_user_by_email(cls, email: str):
        async with async_session_maker() as session:
            try:
                query = select(cls.model).filter_by(email=email)
                result = await session.execute(query)
                user = result.scalar_one_or_none()
                logger.info(f"Пользователь с email {email} найден: {user.username if user else 'не найден'}")
                return user
            except SQLAlchemyError as e:
                logger.error(f"Ошибка при поиске пользователя по email: {e}")
                raise

    @classmethod
    async def update(cls, model_id: int, username: Optional[str] = None, email: Optional[str] = None,
                     hashed_password: Optional[str] = None, firstname: Optional[str] = None):
        async with async_session_maker() as session:
            try:
                stmt = select(Users).where(Users.id == model_id)
                result = await session.execute(stmt)
                user = result.scalar()

                if not user:
                    logger.error(f"Пользователь с id={model_id} не найден.")
                    raise ValueError("Пользователь не найден.")

                logger.info(f"Обновляем пользователя с id={model_id}: username={username}, email={email}")

                if username is not None:
                    user.username = username
                if email is not None:
                    user.email = email
                if hashed_password is not None:
                    user.hashed_password = hashed_password
                if firstname is not None:
                    user.firstname = firstname

                await session.commit()
                logger.info(f"Пользователь с id={model_id} успешно обновлён.")
                return user

            except SQLAlchemyError as e:
                logger.error(f"Ошибка при обновлении пользователя с id={model_id}: {e}")
                await session.rollback()
                raise


class UsersRolesDAO(BaseDAO):
    model = Roles

    @classmethod
    async def add(cls, user_id: int, role_name: str):
        async with async_session_maker() as session:
            try:
                role = await session.execute(
                    select(Roles).where(Roles.name == role_name)
                )
                role = role.scalar_one_or_none()

                if not role:
                    raise ValueError("Роль не найдена")

                existing_association = await session.execute(
                    select(role_user_association).where(
                        (role_user_association.c.user_id == user_id) &
                        (role_user_association.c.role_id == role.id)
                    )
                )
                if existing_association.fetchone():
                    logger.info(f"Пользователь уже имеет роль {role_name}")
                    return

                stmt = insert(role_user_association).values(user_id=user_id, role_id=role.id)
                await session.execute(stmt)
                await session.commit()
                logger.info(f"Роль {role_name} добавлена пользователю с id={user_id}")

            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Ошибка при добавлении роли {role_name} пользователю с id={user_id}: {e}")
                raise

    @classmethod
    async def clear_roles(cls, user_id: int):
        async with async_session_maker() as session:
            try:
                await session.execute(
                    delete(role_user_association).where(
                        role_user_association.c.user_id == user_id
                    )
                )
                await session.commit()
                logger.info(f"Все роли удалены у пользователя с id={user_id}")

            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Ошибка при удалении ролей у пользователя с id={user_id}: {e}")
                raise

    @classmethod
    async def add_roles(cls, user_id: int, role_names: List[str]):
        async with async_session_maker() as session:
            try:
                for role_name in role_names:
                    role = await session.execute(
                        select(Roles).where(Roles.name == role_name)
                    )
                    role = role.scalar_one_or_none()

                    if not role:
                        logger.error(f"Роль {role_name} не найдена")
                        continue

                    existing_association = await session.execute(
                        select(role_user_association).where(
                            (role_user_association.c.user_id == user_id) &
                            (role_user_association.c.role_id == role.id)
                        )
                    )
                    if existing_association.fetchone():
                        logger.info(f"Пользователь уже имеет роль {role_name}")
                        continue

                    stmt = insert(role_user_association).values(user_id=user_id, role_id=role.id)
                    await session.execute(stmt)

                await session.commit()
                logger.info(f"Роли {role_names} успешно добавлены пользователю с id={user_id}")

            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Ошибка при добавлении ролей пользователю с id={user_id}: {e}")
                raise


class UserPermissionsDAO(BaseDAO):
    model = Permissions


class QuestionsDAO(BaseDAO):
    model = Question

    @classmethod
    async def get_all_questions(cls, session: AsyncSession):
        try:
            result = await session.execute(
                select(cls.model).options(selectinload(cls.model.sub_questions))
            )
            questions = result.scalars().all()
            logger.info(f"Получено {len(questions)} вопросов")
            return questions
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении вопросов: {e}")
            raise
