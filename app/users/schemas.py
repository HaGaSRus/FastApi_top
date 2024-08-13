from pydantic import BaseModel, EmailStr


class SUserAuth(BaseModel):
    username: str
    email: EmailStr
    password: str
