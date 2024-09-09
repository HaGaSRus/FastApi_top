from typing import List

import jwt
from fastapi import APIRouter, status, Response, Depends, HTTPException
from jose import JWTError
from pydantic import EmailStr
from sqlalchemy.sql.functions import user

from app.config import settings
from app.logger import logger
from app.users.dao import UsersDAO, UsersRolesDAO
from app.users.auth import (
    get_password_hash,
    authenticate_user,
    create_access_token,
    create_reset_token,
)
from app.users.dependencies import get_current_user, get_current_admin_user
from app.users.models import Users
from app.exceptions import UserInCorrectEmailOrUsername, UserCreated, \
    UserNameAlreadyExistsException, UserEmailAlreadyExistsException
from app.users.schemas import SUserAuth, SUserSignUp, UserResponse, ResetPasswordRequest, ForgotPasswordRequest
from fastapi_versioning import version

from app.utils import send_reset_password_email

router_auth = APIRouter(
    prefix="/auth",
    tags=["Регистрация и изменение данных пользователя"],
)

router_users = APIRouter(
    prefix="/users",
    tags=["Пользователи"]
)


@router_auth.post("/register", status_code=status.HTTP_200_OK)
@version(1)
async def register_user(user_data: SUserAuth):
    users_dao = UsersDAO()
    users_roles_dao = UsersRolesDAO()

    # Проверяем, существует ли уже пользователь с таким username или email
    existing_user_by_username = await users_dao.find_one_or_none(username=user_data.username)
    existing_user_by_email = await users_dao.find_one_or_none(email=user_data.email)

    if existing_user_by_username:
        raise UserNameAlreadyExistsException
    if existing_user_by_email:
        raise UserEmailAlreadyExistsException

    hashed_password = get_password_hash(user_data.password)

    new_user = await users_dao.add(
        username=user_data.username,
        firstname=user_data.firstname,
        lastname=user_data.lastname,
        email=user_data.email,
        hashed_password=hashed_password,
    )

    if new_user:
        await users_roles_dao.add(user_id=new_user.id, role_name="user")

    raise UserCreated


@router_auth.post("/login")
@version(1)
async def login_user(response: Response, user_data: SUserSignUp):
    user = await authenticate_user(user_data.email, user_data.username, user_data.password)
    if not user:
        raise UserInCorrectEmailOrUsername
    access_token = create_access_token({"sub": str(user.id), "username": str(user.username)})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=False,  # Чтобы кука была доступна только для HTTP запросов, а не через JavaScript
        samesite='lax',  # Политика безопасности куки
        secure=False,
        max_age=3600,   # Срок жизни куки в секундах
        expires=3601 ,   # Время истечения срока действия куки

    )
    return {"access_token": access_token}


@router_auth.delete("/delete", status_code=status.HTTP_200_OK)
@version(1)
async def delete_user(user_data: Users = Depends(get_current_user)):
    await UsersDAO.delete(user_data.id)
    return {"message": "User deleted successfully"}


@router_users.get("/me", status_code=status.HTTP_200_OK, response_model=UserResponse)
@version(1)
async def read_users_me(current_user: Users = Depends(get_current_user)):
    user_with_roles = await UsersDAO().get_user_with_roles(current_user.id)
    return user_with_roles


# Эндпоинт для запроса на восстановление пароля
@router_auth.post("/forgot-password", status_code=status.HTTP_200_OK)
@version(1)
async def forgot_password(request: ForgotPasswordRequest):
    email = request.email
    user = await UsersDAO.find_one_or_none(email=email)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь с таким email не найден")

    # Передаем строку email в функцию create_reset_token
    reset_token = create_reset_token(email)
    await send_reset_password_email(email, reset_token)
    return {"message": "Инструкции по восстановлению пароля отправлены на вашу почту."}


# Эндпоинт для сброса пароля
@router_auth.post("/reset-password", status_code=status.HTTP_200_OK)
@version(1)
async def reset_password(reset_password_request: ResetPasswordRequest):
    token = reset_password_request.token
    new_password = reset_password_request.new_password

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        logger.info(f"Токен успешно декодирован: {payload}")

        email: str = payload.get("sub")
        if email is None:
            logger.error("Токен не содержит допустимой темы (email)")
            raise HTTPException(status_code=400, detail="Некорректный токен")
    except JWTError as e:
        logger.error(f"JWT Error: {e}")
        raise HTTPException(status_code=400, detail="Некорректный или истекший токен")

    # Ensure the method exists in UsersDAO
    user = await UsersDAO.get_user_by_email(email)
    if user is None:
        logger.error(f"Пользователь не найден по электронной почте: {email}")
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Обновление пароля
    hashed_password = get_password_hash(new_password)
    await UsersDAO.update(user.id, hashed_password=hashed_password)

    logger.info(f"Пароль для пользователя успешно сброшен: {email}")
    return {"message": "Пароль успешно обновлен"}


@router_users.get("/all-users", status_code=status.HTTP_200_OK, response_model=List[UserResponse])
@version(1)
async def get_all_users(current_user: Users = Depends(get_current_admin_user)) -> List[UserResponse]:
    """Получение всех пользователей. Доступно только администраторам."""
    # Получение всех пользователей
    users_all = await UsersDAO.find_all()
    return users_all