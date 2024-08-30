# app/users/schemas.py

from typing import Optional, List
from pydantic import BaseModel, EmailStr, root_validator


class SUserAuth(BaseModel):
    username: str
    email: EmailStr
    password: str
    firstname: str
    lastname: str


class SUserSignUp(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: str

    @root_validator
    def check_username_or_email(cls, values):
        username, email = values.get('username'), values.get('email')
        if not username and not email:
            raise ValueError("Необходимо указать имя пользователя или почту")
        return values


class Role(BaseModel):
    id: int
    name: str


class UserResponse(BaseModel):
    # id: int
    username: str
    email: str
    # firstname: str
    # lastname: str
    roles: List[Role]  # Измените на список объектов Role

    class Config:
        orm_mode = True
