from typing import Optional
from pydantic import BaseModel, EmailStr, model_validator


class SUserSignUp(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: str

    @model_validator(mode='before')
    def check_username_or_email(cls, values):
        username, email = values.get('username'), values.get('email')
        if not username and not email:
            raise ValueError("Необходимо указать имя пользователя или почту")
        return values


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

