import jwt
from fastapi import APIRouter, status, Response, HTTPException
from jwt.exceptions import ExpiredSignatureError, PyJWTError
from app.auth.auth import get_password_hash, authenticate_user, create_access_token, create_reset_token
from app.config import settings
from app.dao.dao import UsersDAO
from app.exceptions import UserInCorrectEmailOrUsername, PasswordRecoveryInstructions, IncorrectTokenFormatException, \
    TokenExpiredException, UserIsNotPresentException, PasswordUpdatedSuccessfully
from app.logger.logger import logger
from app.auth.schemas import SUserSignUp, ForgotPasswordRequest, ResetPasswordRequest

from app.utils import send_reset_password_email
from fastapi_versioning import version


router_auth = APIRouter(
    prefix="/auth",
    tags=["Регистрация и изменение данных пользователя"],
)


@router_auth.post("/login")
@version(1)
async def login_user(response: Response, user_data: SUserSignUp):
    user = await authenticate_user(user_data.email, user_data.username, user_data.password)
    if not user:
        raise UserInCorrectEmailOrUsername

    # Получаем пользователя с ролями
    user_with_roles = await UsersDAO().get_user_with_roles(user.id)  # Используем экземпляр для вызова метода
    if not user_with_roles:
        raise UserInCorrectEmailOrUsername

    access_token = create_access_token({
        "sub": str(user.id),
        "username": str(user.username),
        "roles": user_with_roles.roles
    })

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=False,  # Чтобы кука была доступна только для HTTP запросов, а не через JavaScript
        samesite='lax',  # Политика безопасности куки
        secure=False,
        max_age=3600,  # Срок жизни куки в секундах
        expires=3601,  # Время истечения срока действия куки
    )
    return {"access_token": access_token}


# Эндпоинт для запроса на восстановление пароля
@router_auth.post("/forgot-password", status_code=status.HTTP_200_OK)
@version(1)
async def forgot_password(request: ForgotPasswordRequest):
    email = request.email
    user = await UsersDAO.find_one_or_none(email=email)
    if not user:
        raise UserInCorrectEmailOrUsername

    # Передаем строку email в функцию create_reset_token
    reset_token = create_reset_token(email)
    await send_reset_password_email(email, reset_token)
    return PasswordRecoveryInstructions


# Эндпоинт для сброса пароля
@router_auth.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(reset_password_request: ResetPasswordRequest):
    token = reset_password_request.token
    new_password = reset_password_request.new_password

    try:
        # Попытка декодирования токена
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        logger.info(f"Токен успешно декодирован: {payload}")

        email: str = payload.get("sub")
        if email is None:
            logger.error("Токен не содержит допустимой темы (email)")
            raise IncorrectTokenFormatException

    # Обработка конкретных исключений
    except ExpiredSignatureError:
        logger.error("Токен истёк")
        raise TokenExpiredException

    except PyJWTError as e:
        logger.error(f"Ошибка JWT: {e}")
        raise TokenExpiredException

    # Убедитесь, что метод существует в UsersDAO
    user = await UsersDAO.get_user_by_email(email)
    if user is None:
        logger.error(f"Пользователь не найден по электронной почте: {email}")
        raise UserIsNotPresentException

    # Обновление пароля
    hashed_password = get_password_hash(new_password)
    await UsersDAO.update(user.id, hashed_password=hashed_password)

    logger.info(f"Пароль для пользователя успешно сброшен: {email}")
    return PasswordUpdatedSuccessfully
