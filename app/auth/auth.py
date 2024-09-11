from typing import Optional

from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

from pydantic import EmailStr

from app.dao.dao import UsersDAO
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=90)):
    to_encode = data.copy()  # убедитесь, что data - это словарь, а не строка
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def authenticate_user(email: Optional[EmailStr], username: Optional[str], password: str):
    user = None
    if email:
        user = await UsersDAO.find_one_or_none(email=email)
    if username:
        user = await UsersDAO.find_one_or_none(username=username)

    if user and verify_password(password, user.hashed_password):
        return user
    return None


def create_reset_token(email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode = {"exp": expire, "sub": email}  # создаем словарь внутри функции
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


