from typing import Optional
import pytz
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from pydantic import EmailStr
from app.dao.dao import UsersDAO
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_current_time_yekaterinburg() -> datetime:
    # Возвращает текущее время в часовом поясе Екатеринбурга
    yekaterinburg_tz = pytz.timezone('Asia/Yekaterinburg')
    return datetime.now(yekaterinburg_tz)


def get_password_hash(password: str) -> str:
    # Хеширует пароль
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Проверяет, совпадает ли введенный пароль с хешированным
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=540)):
    # Создает JWT токен с заданным временем жизни
    to_encode = data.copy()  # Убедитесь, что data — это словарь
    expire = get_current_time_yekaterinburg() + expires_delta
    to_encode.update({"exp": expire.timestamp()})  # Конвертируем время в Unix timestamp
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
    to_encode = {"exp": expire.timestamp(), "sub": email}  # Конвертируем время в Unix timestamp
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
