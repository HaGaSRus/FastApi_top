from app.dao.base import BaseDAO
from app.database import async_session_maker
from app.users.models import Users
from sqlalchemy.future import select


class UsersDAO(BaseDAO):
    model = Users


