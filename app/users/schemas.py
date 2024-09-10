from typing import Optional, List
from pydantic import BaseModel, EmailStr


class Role(BaseModel):
    name: str


class UserResponse(BaseModel):
    username: str
    email: str
    roles: list

    class Config:
        from_attributes = True


class UpdateUserRequest(BaseModel):
    username: Optional[str]
    email: Optional[EmailStr]
    firstname: Optional[str]
    lastname: Optional[str]


class UpdateUserRolesRequest(BaseModel):
    roles: List[str]


