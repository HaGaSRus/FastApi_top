from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings
from app.exceptions import DatabaseExceptions, DatabaseConnectionLost

# Создание асинхронного движка
engine = create_async_engine(settings.DATABASE_URL, echo=False)

# Фабрика сессий
async_session_maker = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Аннотация типов игнорирует предупреждения
async_session_maker: sessionmaker[AsyncSession]


# Зависимость для получения сессии
async def get_db() -> AsyncSession:
    try:
        async with async_session_maker() as session:
            yield session
    except OperationalError as e:
        raise DatabaseConnectionLost(f"База данные потеряла соединение: {str(e)}")
    except SQLAlchemyError as e:
        raise DatabaseExceptions(f"Ошибка ORM: {str(e)}")


# Базовый класс для моделей
class Base(DeclarativeBase):
    pass
