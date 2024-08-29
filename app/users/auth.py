from typing import Optional

from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

from pydantic import EmailStr

from app.users.dao import UsersDAO
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=1)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        settings.ALGORITHM,
    )
    return encoded_jwt

# def create_refresh_token(data: dict) -> str:



async def authenticate_user(email: Optional[EmailStr], username: Optional[str], password: str):
    user = None
    if email:
        user = await UsersDAO.find_one_or_none(email=email)
    if username:
        user = await UsersDAO.find_one_or_none(username=username)

    if user and verify_password(password, user.hashed_password):  # Убедитесь, что атрибут называется hashed_password
        return user
    return None
