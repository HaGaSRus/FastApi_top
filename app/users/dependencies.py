from datetime import datetime

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


def get_token(request: Request):
    """Extracts token from cookies or headers."""
    token = request.cookies.get("access_token")
    if not token:
        token = request.headers.get("access_token")
    if not token:
        logger.error("Token is absent in cookies and headers")
        raise TokenAbsentException
    logger.info(f"Token extracted: {token}")
    return token



async def get_current_user(token: str = Depends(get_token)):
    """Validates the token and retrieves the current user."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        logger.info(f"Token decoded successfully: {payload}")
    except JWTError as e:
        logger.error(f"Token decoding error: {str(e)}")
        raise IncorrectTokenFormatException

    expire: int = payload.get("exp")
    if not expire or int(expire) < datetime.utcnow().timestamp():
        logger.error("Token has expired")
        raise TokenExpiredException

    user_id: str = payload.get("sub")
    if not user_id:
        logger.error("User ID not found in token")
        raise UserIsNotPresentException

    user = await UsersDAO.find_by_id(int(user_id))
    if not user:
        logger.error(f"User with ID {user_id} not found")
        raise UserIsNotPresentException

    logger.info(f"User retrieved: {user}")
    return user


async def get_current_admin_user(current_user: Users = Depends(get_current_user)):
    """Validates that the current user is an admin."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access this resource."
        )
    return current_user
