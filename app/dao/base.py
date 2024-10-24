from typing import Optional

from app.database import async_session_maker
from sqlalchemy import select, insert, update, delete
from app.exceptions import UserNotFoundException
from sqlalchemy.exc import SQLAlchemyError
from app.logger.logger import logger


class BaseDAO:
    model = None

    @classmethod
    async def find_by_id(cls, model_id: int):
        async with async_session_maker() as session:
            try:
                query = select(cls.model).filter_by(id=model_id)
                result = await session.execute(query)
                instance = result.scalar_one_or_none()
                if instance is None:
                    logger.warning(f"Экземпляр с идентификатором {model_id} не найден.")
                return instance
            except SQLAlchemyError as e:
                logger.error(f"Ошибка поиска по идентификатору {model_id}: {e}")
                raise

    @classmethod
    async def find_one_or_none(cls, **filter_by) -> Optional[model]:
        async with async_session_maker() as session:
            try:
                query = select(cls.model).filter_by(**filter_by)
                result = await session.execute(query)
                instance = result.scalar_one_or_none()
                return instance
            except SQLAlchemyError as e:
                logger.error(f"Ошибка при поиске с помощью фильтра {filter_by}: {e}")
                raise

    @classmethod
    async def find_all(cls, **filter_by) -> list:
        async with async_session_maker() as session:
            try:
                query = select(cls.model).filter_by(**filter_by)
                result = await session.execute(query)
                instances = result.scalars().all()
                return instances
            except SQLAlchemyError as e:
                logger.error(f"Ошибка при поиске всех с помощью фильтра {filter_by}: {e}")
                raise

    @classmethod
    async def add(cls, **data) -> model:
        async with async_session_maker() as session:
            try:
                query = insert(cls.model).values(**data).returning(cls.model)
                result = await session.execute(query)
                await session.commit()
                instance = result.scalar_one()
                return instance
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Ошибка при добавлении экземпляра с данными. {data}: {e}")
                raise

    @classmethod
    async def delete(cls, model_id: int):
        async with async_session_maker() as session:
            try:
                query = select(cls.model).filter_by(id=model_id)
                result = await session.execute(query)
                instance = result.scalar_one_or_none()

                if not instance:
                    logger.warning(f"Экземпляр с идентификатором {model_id} не найден для удаления.")
                    raise UserNotFoundException

                stmt = delete(cls.model).where(cls.model.id == model_id)
                await session.execute(stmt)
                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Ошибка удаления экземпляра с идентификатором {model_id}: {e}")
                raise

    @classmethod
    async def update(cls, model_id: int, **data):
        async with async_session_maker() as session:
            try:
                stmt = update(cls.model).where(cls.model.id == model_id).values(**data)
                result = await session.execute(stmt)

                if result.rowcount == 0:
                    logger.warning(f"Экземпляр с идентификатором {model_id} для обновления не найден.")
                    raise UserNotFoundException

                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Ошибка обновления экземпляра с идентификатором {model_id}: {e}")
                raise
