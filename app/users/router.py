from fastapi import APIRouter, HTTPException, status, Response, Depends, Cookie
from starlette.responses import JSONResponse

from app.users.dao import UsersDAO, UsersRolesDAO
from app.users.auth import (
    get_password_hash,
    authenticate_user,
    create_access_token,
)
from app.users.dependencies import get_current_user, get_current_admin_user
from app.users.models import Users
from app.exceptions import UserAlreadyExistsException, UserInCorrectEmailOrUsername, UserCreated
from app.users.schemas import SUserAuth, SUserSingUp
from fastapi_versioning import version
from app.logger import logger

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
    existing_user = await UsersDAO.find_one_or_none(email=user_data.email)
    if existing_user:
        raise UserAlreadyExistsException

    hashed_password = get_password_hash(user_data.password)

    await UsersDAO.add(
        username=user_data.username,
        firstname=user_data.firstname,
        lastname=user_data.lastname,
        email=user_data.email,
        hashed_password=hashed_password,
    )

    new_user = await UsersDAO.find_one_or_none(email=user_data.email)
    if new_user:
        await UsersRolesDAO.add(user_id=new_user.id, role_name="user")
    raise UserCreated

@router_auth.get("/")
def root(last_visit = Cookie()):
    return  {"last visit": last_visit}

@router_auth.post("/login")
@version(1)
async def login_user(response: Response, user_data: SUserSingUp):
    user = await authenticate_user(user_data.email, user_data.username, user_data.password)
    if not user:
        raise UserInCorrectEmailOrUsername
    access_token = create_access_token({"sub": str(user.id)})
    response.set_cookie(
        key="access_token",
        value=access_token,
        # domain="http://192.168.188.53:8080",
        httponly=False,  # Чтобы кука была доступна только для HTTP запросов, а не через JavaScript
        samesite='lax',  # Политика безопасности куки
        secure=False,
        max_age=86400,   # Срок жизни куки в секундах
        expires=86400 ,   # Время истечения срока действия куки

    )
    return {"access_token": access_token}



@router_auth.post("/logout", status_code=status.HTTP_200_OK)
@version(1)
async def logout_user(response: Response):
    # Удаление куки при выходе
    response.delete_cookie("access_token")
    return {"message": "Successfully logged out"}

@router_auth.delete("/delete", status_code=status.HTTP_200_OK)
@version(1)
async def delete_user(user_data: Users = Depends(get_current_user)):
    await UsersDAO.delete(user_data.id)
    return {"message": "User deleted successfully"}

@router_users.get("/me", status_code=status.HTTP_200_OK)
@version(1)
async def read_users_me(current_user: Users = Depends(get_current_user)):
    # Возвращает данные текущего пользователя
    return current_user

# @router.get("/all")
# async def read_users_me(current_user: Users = Depends(get_current_admin_user)):
#     return await UsersDAO.find_all()


