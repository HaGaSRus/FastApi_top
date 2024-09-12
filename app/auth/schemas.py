from typing import Optional
from pydantic import BaseModel, EmailStr, model_validator, Field


class SUserSignUp(BaseModel):
    username: Optional[str] = Field(None, min_length=1, max_length=50, description="Имя пользователя должно быть от 1 до 50 символов")
    email: Optional[EmailStr] = None
    password: str = Field(..., min_length=6, description="Пароль должен содержать не менее 6 символов")

    @model_validator(mode='before')
    def check_username_or_email(cls, values):
        username, email = values.get('username'), values.get('email')
        if not username and not email:
            raise ValueError("Необходимо указать имя пользователя или почту")
        return values


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6, description="Пароль должен содержать не менее 6 символов")


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

