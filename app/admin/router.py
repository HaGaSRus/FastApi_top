from typing import List

from fastapi import APIRouter, status, Depends
from fastapi_versioning import version

from app.auth.auth import get_password_hash
from app.dao.dao import UsersDAO, UsersRolesDAO
from app.dao.dependencies import get_current_admin_user
from app.database import async_session_maker
from app.exceptions import UserEmailAlreadyExistsException, UserNameAlreadyExistsException, UserCreated, UserChangeRole, \
    DeleteUser
from app.users.models import Users
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select

from app.users.schemas import UserSchema, Role, UpdateUserRequest, UpdateUserRolesRequest
from app.admin.schemas import SUserAuth

router_admin = APIRouter(
    prefix="/auth",
    tags=["Админка"],
)


@router_admin.post("/register", status_code=status.HTTP_201_CREATED)
@version(1)
async def register_user(user_data: SUserAuth, current_user: Users = Depends(get_current_admin_user)):
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


@router_admin.get("/all-users", status_code=status.HTTP_200_OK, response_model=List[UserSchema])
@version(1)
async def get_all_users(current_user: Users = Depends(get_current_admin_user)) -> List[UserSchema]:
    """Получение всех пользователей. Доступно только администраторам."""
    async with async_session_maker() as session:
        users_all = await session.execute(
            select(Users).options(selectinload(Users.roles))
        )
        users_all = users_all.scalars().all()

    user_responses = [UserSchema(
        id=user.id,
        username=user.username,
        email=user.email,
        firstname=user.firstname,
        lastname=user.lastname,
        roles=[Role(name=role.name) for role in user.roles],
    ) for user in users_all]

    return user_responses


@router_admin.post("/update-admin", status_code=status.HTTP_200_OK, response_model=UserSchema)
@version(1)
async def update_user_admin(
        update_data: UpdateUserRequest,
        current_user: Users = Depends(get_current_admin_user),
):
    """Обновление информации о пользователе. Только для администратора"""
    users_dao = UsersDAO()

    # Проверка, существует ли такой пользователь
    if update_data.username:
        existing_user = await users_dao.find_one_or_none(username=update_data.username)
        if existing_user and existing_user.id != current_user.id:
            raise UserNameAlreadyExistsException

    if update_data.email:
        existing_user = await users_dao.find_one_or_none(email=update_data.email)
        if existing_user and existing_user.id != current_user.id:
            raise UserEmailAlreadyExistsException

    # Обновляем данные пользователя
    updated_user = await users_dao.update(
        model_id=current_user.id,
        username=update_data.username,
        email=update_data.email,
        firstname=update_data.firstname,
        lastname=update_data.lastname,
    )

    return updated_user


@router_admin.post("/update-roles", status_code=status.HTTP_200_OK)
@version(1)
async def update_user_roles(
        user_id: int,
        update_roles: UpdateUserRolesRequest,
        current_user: Users = Depends(get_current_admin_user),
):
    """Изменение или добавление ролей пользователю. Только для администратора"""
    users_roles_dao = UsersRolesDAO()

    # Очистка текущих ролей и добавление новых ролей
    await users_roles_dao.clear_roles(user_id=user_id)  # Очистка ролей
    await users_roles_dao.add_roles(user_id=user_id, role_names=update_roles.roles)  # Добавление новых ролей

    return UserChangeRole


@router_admin.delete("/delete", status_code=status.HTTP_200_OK)
@version(1)
async def delete_user(user_id: int, current_user: Users = Depends(get_current_admin_user)):
    """Удаление пользователя. Только для администратора"""
    users_dao = UsersDAO()
    await users_dao.delete(user_id)
    return DeleteUser
