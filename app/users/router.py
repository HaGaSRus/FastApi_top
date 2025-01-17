from fastapi import APIRouter, status, Depends
from app.auth.auth import pwd_context
from app.dao.dao import UsersDAO
from app.dao.dependencies import get_current_user
from app.logger.logger import logger
from app.users.models import Users
from app.exceptions import UserNameAlreadyExistsException, UserEmailAlreadyExistsException, UpdateUser, \
    ErrorUpdatingUser
from app.users.schemas import UserResponse, UpdateUserRequest
from fastapi_versioning import version


router_users = APIRouter(
    prefix="/users",
    tags=["Пользователи"],
)


@router_users.get("/me", status_code=status.HTTP_200_OK, response_model=UserResponse, summary="Отображение пользователя")
@version(1)
async def read_users_me(current_user: Users = Depends(get_current_user)):
    """Пользователь получает отображение всех своих данных"""
    user_with_roles = await UsersDAO().get_user_with_roles(current_user.id)
    return user_with_roles


@router_users.post("/update", status_code=status.HTTP_200_OK, summary="Обновление пользователя")
@version(1)
async def update_user(
        update_data: UpdateUserRequest,
        current_user: Users = Depends(get_current_user),
):
    """Обновление информации о пользователе"""
    users_dao = UsersDAO()

    if update_data.username:
        existing_user = await users_dao.find_one_or_none(username=update_data.username)
        if existing_user and existing_user.id != current_user.id:
            logger.warning(f"Имя пользователя {update_data.username} уже используется.")
            raise UserNameAlreadyExistsException

    if update_data.email:
        existing_user = await users_dao.find_one_or_none(email=update_data.email)
        if existing_user and existing_user.id != current_user.id:
            logger.warning(f"Email {update_data.email} уже используется.")
            raise UserEmailAlreadyExistsException

    hashed_password = pwd_context.hash(update_data.password) if update_data.password else None

    try:
        await users_dao.update(
            model_id=current_user.id,
            username=update_data.username,
            email=update_data.email,
            hashed_password=hashed_password,
            firstname=update_data.firstname,
        )
    except Exception as e:
        logger.warning(f"Ошибка обновления пользователя: {e}")
        raise ErrorUpdatingUser

    return UpdateUser
