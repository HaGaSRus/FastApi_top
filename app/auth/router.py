import jwt
from fastapi import APIRouter, status, Response
from jwt.exceptions import ExpiredSignatureError, PyJWTError
from app.auth.auth import get_password_hash, create_access_token, create_reset_token, verify_password, \
    create_refresh_token, refresh_access_token
from app.config import settings
from app.dao.dao import UsersDAO
from app.exceptions import UserInCorrectEmailOrUsername, PasswordRecoveryInstructions, IncorrectTokenFormatException, \
    TokenExpiredException, UserIsNotPresentException, PasswordUpdatedSuccessfully, EmailOrUsernameWasNotFound, \
    InvalidPassword, FailedToGetUserRoles, HootLineException, ErrorGettingUser
from app.logger.logger import logger
from app.auth.schemas import SUserSignUp, ForgotPasswordRequest, ResetPasswordRequest, RefreshTokenRequest

from app.utils import send_reset_password_email
from fastapi_versioning import version


router_auth = APIRouter(
    prefix="/auth",
    tags=["Регистрация и изменение данных пользователя"],
)


@router_auth.post("/login", summary="Авторизация пользователя")
@version(1)
async def login_user(response: Response, user_data: SUserSignUp):
    """Логика авторизации для входа на горячую линию"""
    users_dao = UsersDAO()
    try:
        user = (await users_dao.find_one_or_none(email=user_data.email)
                or await users_dao.find_one_or_none(username=user_data.username))

        if not user:
            logger.error("Пользователь не найден")
            raise EmailOrUsernameWasNotFound()

        if not verify_password(user_data.password, user.hashed_password):
            logger.error("Неверный пароль")
            raise InvalidPassword()

        user_with_roles = await users_dao.get_user_with_roles(user.id)
        if not user_with_roles:
            logger.error("Не удалось получить роли пользователя")
            raise FailedToGetUserRoles()

        access_token = create_access_token({
            "sub": str(user.id),
            "username": str(user.username),
            "roles": user_with_roles.roles
        })

        refresh_token = create_refresh_token({
            "sub": str(user.id),
            "username": str(user.username),
            "roles": user_with_roles.roles
        })

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=False,
            samesite='lax',
            secure=False,
            max_age=86400,
            expires=86401,
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=False,
            samesite='lax',
            secure=False,
            max_age=604800,  # 30 дней
            expires=604801,
        )

        return {"access_token": access_token, "refresh_token": refresh_token}
    except Exception as e:
        logger.error(f"Ошибка при авторизации: {e}")
        return ErrorGettingUser


@router_auth.post("/forgot-password",
                  status_code=status.HTTP_200_OK,
                  summary="Форма-восстановления пароля для пользователя")
@version(1)
async def forgot_password(request: ForgotPasswordRequest):
    """ Восстановление пароля для пользователя, логика отправки формы на почту"""
    users_dao = UsersDAO()
    user = await users_dao.find_one_or_none(email=request.email)
    if not user:
        raise UserInCorrectEmailOrUsername

    reset_token = create_reset_token(request.email)
    await send_reset_password_email(request.email, reset_token)
    return PasswordRecoveryInstructions


@router_auth.post("/reset-password", status_code=status.HTTP_200_OK, summary="Форма ввода нового пароля")
async def reset_password(reset_password_request: ResetPasswordRequest):
    """Логика обновления пароля после перехода по ссылке для восстановления"""
    token = reset_password_request.token
    new_password = reset_password_request.new_password

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        logger.info(f"Токен успешно декодирован: {payload}")

        email: str = payload.get("sub")
        if email is None:
            logger.error("Токен не содержит допустимой темы (email)")
            raise IncorrectTokenFormatException

    except ExpiredSignatureError:
        logger.error("Токен истёк")
        raise TokenExpiredException

    except PyJWTError as e:
        logger.error(f"Ошибка JWT: {e}")
        raise IncorrectTokenFormatException

    users_dao = UsersDAO()
    user = await users_dao.get_user_by_email(email)
    if user is None:
        logger.error(f"Пользователь не найден по электронной почте: {email}")
        raise UserIsNotPresentException

    hashed_password = get_password_hash(new_password)
    await users_dao.update(user.id, hashed_password=hashed_password)

    logger.info(f"Пароль для пользователя успешно сброшен: {email}")
    return PasswordUpdatedSuccessfully


@router_auth.post("/token/refresh", summary="Обновление access токена")
@version(1)
async def refresh_token(request: RefreshTokenRequest):
    """Обновление access токена с использованием рефреш токена"""
    refresh_token = request.refresh_token
    return await refresh_access_token(refresh_token)
