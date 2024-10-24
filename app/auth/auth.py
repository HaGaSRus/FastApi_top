from typing import Optional
import pytz
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from pydantic import EmailStr
from app.dao.dao import UsersDAO
from app.config import settings
from app.exceptions import InvalidRefreshToken, EmailOrUsernameWasNotFound, RefreshTokenHasExpired, FailedToGetUserRoles
from app.logger.logger import logger

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_current_time_yekaterinburg() -> datetime:
    yekaterinburg_tz = pytz.timezone('Asia/Yekaterinburg')
    return datetime.now(yekaterinburg_tz)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=24)):
    to_encode = data.copy()
    expire = get_current_time_yekaterinburg() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def authenticate_user(email: Optional[EmailStr], username: Optional[str], password: str):
    users_dao = UsersDAO()
    user = None
    if email:
        user = await users_dao.find_one_or_none(email=email)
    elif username:
        user = await users_dao.find_one_or_none(username=username)

    if user and verify_password(password, user.hashed_password):
        return user
    return None


def create_reset_token(email: str) -> str:
    expire = get_current_time_yekaterinburg() + timedelta(minutes=15)
    to_encode = {"exp": expire, "sub": email}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: timedelta = timedelta(days=7)):
    to_encode = data.copy()
    expire = get_current_time_yekaterinburg() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def refresh_access_token(refresh_token: str):
    """Обновляет access токен на основе рефреш токена."""
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        user_id = int(payload.get("sub"))
        if user_id is None:
            logger.error("Рефреш токен не содержит идентификатор пользователя")
            raise InvalidRefreshToken

        users_dao = UsersDAO()
        user = await users_dao.find_one_or_none(id=user_id)
        if user is None:
            logger.error(f"Пользователь с id '{user_id}' не найден")
            raise EmailOrUsernameWasNotFound

        user_with_roles = await users_dao.get_user_with_roles(user.id)
        if not user_with_roles:
            logger.error("Не удалось получить роли пользователя")
            raise FailedToGetUserRoles()


        access_token = create_access_token(data={
            "sub": str(user.id),
            "username": str(user.username),
            "roles": user_with_roles.roles
        })

        return {"access_token": access_token}
    except jwt.ExpiredSignatureError:
        logger.error("Рефреш токен истек")
        raise RefreshTokenHasExpired
    except jwt.JWTError as e:
        logger.error(f"Ошибка JWT: {e}")
        raise InvalidRefreshToken


