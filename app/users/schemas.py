from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class SUserAuth(BaseModel):
    username: str
    email: EmailStr
    password: str
    firstname: str
    lastname: str



class SUserSingUp(BaseModel):
    username: str
    email: EmailStr
    password: str