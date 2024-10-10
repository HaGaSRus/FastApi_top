from datetime import datetime
from fastapi import Request, Depends, Response, HTTPException
from jose import jwt, JWTError
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.config import settings
from app.database import async_session_maker
from app.exceptions import (
    TokenAbsentException,
    UserIsNotPresentException, PermissionDeniedException, ErrorGettingUser,
)
from app.logger.logger import logger

from app.users.models import Users


def get_token(request: Request) -> str:
    """Извлекает токен из файлов cookie или заголовков."""
    logger.info(f"Куки при запросе: {request.cookies}")  # Логируем куки

    token = request.cookies.get("access_token")
    if not token:
        token = request.headers.get("access_token")
    if not token:
        logger.error("Токен отсутствует в файлах cookie и заголовках.")
        raise TokenAbsentException
    logger.info(f"Токен извлечен: {token}")
    return token


async def get_current_user(response: Response, token: str = Depends(get_token)):
    """Проверяем токен и получаем текущего пользователя."""
    if not token:
        logger.error("Токен отсутствует.")
        raise TokenAbsentException

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        logger.info(f"Токен успешно декодирован: {payload}")
    except JWTError as e:
        logger.error(f"Ошибка декодирования токена: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"})

    expire = payload.get("exp")
    if not expire or int(expire) < datetime.now().timestamp():
        logger.error("Срок действия токена истек.")
        raise HTTPException(status_code=401, detail="Token expired", headers={"WWW-Authenticate": "Bearer"})

    user_id = payload.get("sub")
    if not user_id:
        logger.error("Идентификатор пользователя не найден в токене.")
        raise UserIsNotPresentException

    async with async_session_maker() as session:
        try:
            result = await session.execute(
                select(Users).options(selectinload(Users.roles)).where(Users.id == int(user_id))
            )
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"Пользователь с идентификатором {user_id} не найден.")
                raise UserIsNotPresentException

            logger.info(f"Пользователь получен: {user.username}")
            return user
        except Exception as e:
            logger.error(f"Необработанная ошибка при получении пользователя: {e}")
            raise ErrorGettingUser


async def get_current_admin_user(current_user: Users = Depends(get_current_user)) -> Users:
    """Проверяет, является ли текущий пользователь администратором."""
    if not current_user or not any(role.name == "admin" for role in current_user.roles):
        logger.error("Пользователь не является администратором.")
        raise PermissionDeniedException

    logger.info(f"Администратор авторизован: {current_user.username}")
    return current_user


async def get_current_admin_or_moderator_user(current_user: Users = Depends(get_current_user)) -> tuple[Users, str]:
    """Проверяем, является ли текущий пользователь администратором или модератором и возвращает его роль."""
    if not current_user:
        logger.error("Пользователь не авторизован.")
        raise PermissionDeniedException

    roles = {role.name for role in current_user.roles}
    if "admin" in roles:
        logger.info(f"Администратор авторизирован: {current_user.username}")
        return current_user, "admin"
    elif "moderator" in roles:
        logger.info(f"Модератор авторизирован: {current_user.username}")
        return current_user, "moderator"
    else:
        logger.error("Пользователь не имеет прав администратора или модератора.")
        raise PermissionDeniedException
