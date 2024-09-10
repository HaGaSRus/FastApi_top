from datetime import datetime
from typing import Optional

from fastapi import Request, Depends, HTTPException
from jose import jwt, JWTError
from starlette import status

from app.config import settings
from app.exceptions import (
    TokenExpiredException,
    TokenAbsentException,
    IncorrectTokenFormatException,
    UserIsNotPresentException,
)
from app.logger import logger
from app.users.dao import UsersDAO
from app.users.models import Users

def get_token(request: Request) -> str:
    """Извлекает токен из файлов cookie или заголовков."""
    token = request.cookies.get("access_token")
    if not token:
        token = request.headers.get("access_token")
    if not token:
        logger.error("Токен отсутствует в файлах cookie и заголовках.")
        raise TokenAbsentException
    logger.info(f"Токен извлечен: {token}")
    return token

async def get_current_user(token: str = Depends(get_token)) -> Users:
    """Проверяем токен и получаем текущего пользователя."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        logger.info(f"Токен успешно декодирован: {payload}")
    except JWTError as e:
        logger.error(f"Ошибка декодирования токена: {str(e)}")
        raise IncorrectTokenFormatException

    expire: Optional[int] = payload.get("exp")
    if not expire or int(expire) < datetime.utcnow().timestamp():
        logger.error("Срок действия токена истек")
        raise TokenExpiredException

    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        logger.error("Идентификатор пользователя не найден в токене")
        raise UserIsNotPresentException

    user = await UsersDAO.find_by_id(int(user_id))
    if not user:
        logger.error(f"Пользователь с идентификатором {user_id} не найден")
        raise UserIsNotPresentException

    logger.info(f"Пользователь получен: {user}")
    return user

async def get_current_admin_user(current_user: Users = Depends(get_current_user)) -> Users:
    """Проверяет, что текущий пользователь является администратором."""
    if getattr(current_user, 'role', None) != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет разрешения на доступ к этому ресурсу."
        )
    return current_user
