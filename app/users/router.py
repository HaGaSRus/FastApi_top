from fastapi import APIRouter, HTTPException, status, Response, Depends
from app.users.dao import UsersDAO, UserPermissionsDAO, UsersRolesDAO
from app.users.auth import (
    get_password_hash,
    verify_password,
    authenticate_user,
    create_access_token,
)
from app.users.dependencies import get_current_user, get_current_admin_user
from app.users.models import Users
from app.exceptions import UserAlreadyExistsException, IncorrectEmailOrPasswordException

from app.users.schemas import SUserAuth, SUserSingUp

router_auth = APIRouter(
    prefix="/auth",
    tags=["Регистрация и изменение данных пользователя"],
)

router_users = APIRouter(
    prefix="/users",
    tags=["Пользователи"]
)


@router_auth.post("/register",status_code=status.HTTP_200_OK)
async def register_user(user_data: SUserAuth):
    existing_user = await UsersDAO.find_one_or_none(email=user_data.email)
    if existing_user:
        raise UserAlreadyExistsException

    hashed_password = get_password_hash(user_data.password)

    # Добавление пользователя
    await UsersDAO.add(
        username=user_data.username,
        firstname=user_data.firstname,
        lastname=user_data.lastname,
        email=user_data.email,
        hashed_password=hashed_password,
    )

    new_user = await UsersDAO.find_one_or_none(email=user_data.email)
    if new_user:
        # Назначение базовой роли
        await UsersRolesDAO.add(user_id=new_user.id, role_name="user")

    return {"message": "User registered successfully"}


@router_auth.post("/login")
async def login_user(response: Response, user_data: SUserSingUp):
    user = await authenticate_user(user_data.email, user_data.password)
    if not user:
        raise IncorrectEmailOrPasswordException
    access_token = create_access_token({"sub": str(user.id)})
    response.set_cookie("booking_access_token", access_token, httponly=True)
    return {"access_token": access_token}


@router_auth.post("/logout")
async def logout_user(response: Response):
    response.delete_cookie("booking_access_token")


@router_auth.delete("/delete")
async def delete_user(user_data: Users = Depends(get_current_user)):
    await UsersDAO.delete(user_data.id)


@router_users.get("/me")
async def read_users_me(current_user: Users = Depends(get_current_user)):
    return current_user


# @router.get("/all")
# async def read_users_me(current_user: Users = Depends(get_current_admin_user)):
#     return await UsersDAO.find_all()