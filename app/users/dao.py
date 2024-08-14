from typing import Optional

from pydantic import Field

from app.dao.base import BaseDAO
from app.database import async_session_maker
from app.users.models import Users, UsersRoles, UsersPermissions
from sqlalchemy.future import select


class UsersDAO(BaseDAO):
    model = Users


class UsersRolesDAO(BaseDAO):
    model = UsersRoles


class UserPermissionsDAO(BaseDAO):
    model = UsersPermissions

