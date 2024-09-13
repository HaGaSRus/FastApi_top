from fastapi import APIRouter, Depends, status, Query, HTTPException
from fastapi_pagination import paginate, Page, Params, add_pagination
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.admin.schemas import UserFilter
from app.dao.dependencies import get_current_admin_user
from app.database import async_session_maker
from fastapi_versioning import version
from fastapi_filter import FilterDepends
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
    try:
        async with async_session_maker() as session:
            stmt = select(Users).options(selectinload(Users.roles)).limit(params.size).offset((params.page - 1) * params.size)
            result = await session.execute(stmt)
            users_all = result.scalars().all()

        user_responses = [
            AllUserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                firstname=user.firstname,
                roles=[Role(name=role.name) for role in user.roles],
            ) for user in users_all
        ]

        # Применение кастомных параметров пагинации
        return paginate(user_responses, params=params)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_filter.get("/users", response_model=Page[AllUserResponse])
@version(1)
async def get_filtered_users(
    user_filter: UserFilter = FilterDepends(UserFilter),
    page: int = Query(default=1, alias="page"),
    size: int = Query(default=10, alias="size")
):
    """Получение пользователей с применением фильтров и пагинации."""
    async with async_session_maker() as session:
        query = select(Users).options(selectinload(Users.roles))

        # Применяем фильтры к запросу
        filtered_query = user_filter.apply_filter(query)

        # Выполняем запрос к базе данных
        result = await session.execute(filtered_query)
        users_all = result.scalars().all()

        # Применяем пагинацию
        return paginate(users_all, Params(page=page, size=size))
