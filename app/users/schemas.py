from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class SUserAuth(BaseModel):
    username: str
    email: EmailStr
    password: str
    firstname: str
    lastname: str
    roles_user: Optional[str] = Field(default="User")


class SUserSingUp(BaseModel):
    username: str
    email: EmailStr
    password: str