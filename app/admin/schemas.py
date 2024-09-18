from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy import or_
from app.users.models import Users
from app.users.schemas import UpdateUserRequest
from fastapi_filter.contrib.sqlalchemy import Filter


class SUserAuth(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, description="Имя пользователя не может быть пустым")
    email: EmailStr
    password: str = Field(..., min_length=6, description="Пароль должен содержать не менее 6 символов")
    firstname: str = Field(..., min_length=1, description="Имя не может быть пустым")

    @model_validator(mode="before")
    def check_required_fields(cls, values):
        # Проверяем, что все обязательные поля заполнены
        required_fields = ["username", "email", "password", "firstname"]
        for field in required_fields:
            if not values.get(field):
                raise ValueError(f"Поле {field} не может быть пустым")
        return values


class UpdateUserRequestWithId(BaseModel):
    user_id: int
    update_data: UpdateUserRequest


class UserIdRequest(BaseModel):
    user_id: int


class UserFilter(Filter):
    username: Optional[str] = None
    email: Optional[str] = None
    firstname: Optional[str] = None
    username__ilike: Optional[str] = None  # Частичное совпадение
    email__ilike: Optional[str] = None  # Частичное совпадение
    firstname__ilike: Optional[str] = None  # Частичное совпадение
    order_by: List[str] = ["id"]
    search: Optional[str] = None  # Параметр поиска по всем полям

    class Constants(Filter.Constants):
        model = Users
        search_model_fields = ["username", "email", "firstname"]

    def apply_filter(self, query):
        if self.search:
            search_value = f"%{self.search}%"
            query = query.where(
                or_(
                    Users.username.ilike(search_value),
                    Users.email.ilike(search_value),
                    Users.firstname.ilike(search_value),
                )
            )
        else:
            if self.username:
                query = query.where(Users.username.ilike(f"%{self.username}%"))

            if self.email:
                query = query.where(Users.email.ilike(f"%{self.email}%"))

            if self.firstname:
                query = query.where(Users.firstname.ilike(f"%{self.firstname}%"))

        return query



