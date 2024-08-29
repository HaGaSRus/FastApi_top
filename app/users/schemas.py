from typing import Optional

from pydantic import BaseModel, EmailStr, root_validator


class SUserAuth(BaseModel):
    username: str
    email: EmailStr
    password: str
    firstname: str
    lastname: str


class SUserSingUp(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: str

    @root_validator
    def check_username_or_email(cls, values):
        username, email = values.get('username'), values.get('email')
        if not username and not email:
            raise ValueError("Необходимо указать имя пользователя или почту")
        return values


class UserResponse(BaseModel):
    username: str
    firstname: str

    class Config:
        orm_mode = True


