from typing import Optional

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.users.models import Users
from app.users.schemas import UpdateUserRequest
from fastapi_filter.contrib.sqlalchemy import Filter

class SUserAuth(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, description="Имя пользователя не может быть пустым")
    email: EmailStr
    password: str = Field(..., min_length=6, description="Пароль должен содержать не менее 6 символов")
    firstname: str = Field(..., min_length=1, description="Имя не может быть пустым")
    lastname: str = Field(..., min_length=1, description="Фамилия не может быть пустой")

    @model_validator(mode="before")
    def check_required_fields(cls, values):
        # Проверяем, что все обязательные поля заполнены
        required_fields = ["username", "email", "password", "firstname", "lastname"]
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
    lastname: Optional[str] = None

    class Constants(Filter.Constants):
        model = Users
        search_model_fields = ["username", "email", "firstname", "lastname"]

