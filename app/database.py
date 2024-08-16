from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.future import select
from app.config import settings


# Создание асинхронного движка
engine = create_async_engine(settings.DATABASE_URL)

# Фабрика сессий
async_session_maker = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

# Базовый класс для моделей
class Base(DeclarativeBase):
    pass


