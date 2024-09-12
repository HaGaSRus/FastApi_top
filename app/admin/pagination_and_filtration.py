from fastapi import APIRouter, Depends, status
from fastapi_pagination import paginate, Page, Params, add_pagination
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.dao.dependencies import get_current_admin_user
from app.database import async_session_maker
from fastapi_versioning import version

from app.users.models import Users
from app.users.schemas import AllUserResponse, Role

# Создаем роутер
router_pagination = APIRouter(
    prefix="/auth",
    tags=["Пагинация"],
)

router_filter = APIRouter(
    prefix="/filter",
    tags=["Фильтрация"],
)

# Параметры по умолчанию для пагинации
DEFAULT_PAGE_SIZE = 10  # Количество элементов на странице по умолчанию
MAX_PAGE_SIZE = 100  # Максимальное количество элементов на странице


# Класс для кастомных параметров пагинации
class CustomParams(Params):
    size: int = DEFAULT_PAGE_SIZE  # Устанавливаем значение по умолчанию
    max_size: int = MAX_PAGE_SIZE  # Максимальное количество элементов


# Регистрируем пагинацию в FastAPI
add_pagination(router_pagination)


@router_pagination.get("/all-users", status_code=status.HTTP_200_OK, response_model=Page[AllUserResponse])
@version(1)
async def get_all_users(
    current_user: Users = Depends(get_current_admin_user),
    params: CustomParams = Depends()  # Используем кастомные параметры пагинации
):
    """Получение всех пользователей. Доступно только администраторам."""
    async with async_session_maker() as session:
        users_all = await session.execute(
            select(Users).options(selectinload(Users.roles))
        )
        users_all = users_all.scalars().all()

    user_responses = [
        AllUserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            firstname=user.firstname,
            lastname=user.lastname,
            roles=[Role(name=role.name) for role in user.roles],
        ) for user in users_all
    ]

    # Применение кастомных параметров пагинации
    return paginate(user_responses, params=params)
