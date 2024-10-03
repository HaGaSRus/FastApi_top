from typing import Optional
import pytz
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from pydantic import EmailStr
from app.dao.dao import UsersDAO
from app.config import settings
from app.exceptions import InvalidRefreshToken, EmailOrUsernameWasNotFound, RefreshTokenHasExpired
from app.logger.logger import logger

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_current_time_yekaterinburg() -> datetime:
    # Возвращает текущее время в часовом поясе Екатеринбурга
    yekaterinburg_tz = pytz.timezone('Asia/Yekaterinburg')
    return datetime.now(yekaterinburg_tz)


def get_password_hash(password: str) -> str:
    # Хэширует пароль
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Проверяет, совпадает ли введенный пароль с хэшированным
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=540)):
    # Создает JWT токен с заданным временем жизни
    to_encode = data.copy()  # Убедитесь, что data — это словарь
    expire = get_current_time_yekaterinburg() + expires_delta
    to_encode.update({"exp": expire})  # Передаем datetime объект напрямую
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def authenticate_user(email: Optional[EmailStr], username: Optional[str], password: str):
    users_dao = UsersDAO()  # Создание экземпляра
    user = None
    if email:
        user = await users_dao.find_one_or_none(email=email)
    elif username:
        user = await users_dao.find_one_or_none(username=username)

    if user and verify_password(password, user.hashed_password):
        return user
    return None


def create_reset_token(email: str) -> str:
    # Создает JWT токен для сброса пароля с заданным временем жизни
    expire = get_current_time_yekaterinburg() + timedelta(minutes=15)
    to_encode = {"exp": expire, "sub": email}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: timedelta = timedelta(days=30)):
    # Создаем рефреш токен с заданным временем жизни
    to_encode = data.copy()
    expire = get_current_time_yekaterinburg() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def refresh_access_token(refresh_token: str):
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        logger.info(f"Рефреш токен успешно декодирован: {payload}")

        email = payload.get("sub")
        if email is None:
            logger.error(f"Рефреш токен не содержит допустимой темы {email}")
            raise InvalidRefreshToken

        # Получение пользователя по email
        users_dao = UsersDAO()
        user = await users_dao.find_one_or_none(email=email)
        if user is None:
            raise EmailOrUsernameWasNotFound

        access_token = create_access_token(data={"sub": user.email})
        return {"access_token": access_token}
    except jwt.ExpiredSignatureError:
        logger.error("Рефреш токен истёк")
        raise RefreshTokenHasExpired
    except jwt.JWTError as e:
        logger.error(f"Ошибка JWT: {e}")
        raise InvalidRefreshToken

