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
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None


class UpdateUserRolesRequest(BaseModel):
    roles: List[str]


