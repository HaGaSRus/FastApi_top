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
    tags=["Пользователи"]
)


@router_users.get("/me", status_code=status.HTTP_200_OK, response_model=UserResponse)
@version(1)
async def read_users_me(current_user: Users = Depends(get_current_user)):
    user_with_roles = await UsersDAO().get_user_with_roles(current_user.id)
    return user_with_roles


@router_users.post("/update", status_code=status.HTTP_200_OK)
@version(1)
async def update_user(
        update_data: UpdateUserRequest,
        current_user: Users = Depends(get_current_user),
):
    """Обновление информации о пользователе"""
    users_dao = UsersDAO()

    # Проверка, существует ли такой пользователь
    if update_data.username:
        existing_user = await users_dao.find_one_or_none(username=update_data.username)
        if existing_user and existing_user.id != current_user.id:
            logger.error(f"Имя пользователя {update_data.username} уже используется.")
            raise UserNameAlreadyExistsException

    if update_data.email:
        existing_user = await users_dao.find_one_or_none(email=update_data.email)
        if existing_user and existing_user.id != current_user.id:
            logger.error(f"Email {update_data.email} уже используется.")
            raise UserEmailAlreadyExistsException

    hashed_password = pwd_context.hash(update_data.password) if update_data.password else None

    # Логирование перед обновлением
    logger.info(
        f"Обновление пользователя с id={current_user.id}: "
        f"username={update_data.username}, email={update_data.email}, "
        f"hashed_password={'Yes' if hashed_password else 'No'}"
    )

    try:
        # Обновляем данные пользователя
        await users_dao.update(
            model_id=current_user.id,
            username=update_data.username,
            email=update_data.email,
            hashed_password=hashed_password,
            firstname=update_data.firstname,
            lastname=update_data.lastname,
        )
    except Exception as e:
        logger.error(f"Ошибка обновления пользователя: {e}")
        raise ErrorUpdatingUser

    return UpdateUser
