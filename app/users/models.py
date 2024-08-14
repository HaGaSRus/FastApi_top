from sqlalchemy import Column, Integer, String, ForeignKey, text, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.database import Base


class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, nullable=False)

    username = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    hashed_password = Column(String, nullable=False)
    firstname = Column(String, nullable=False)
    lastname = Column(String, nullable=False)
    # is_superuser = Column(Boolean, default=False)
    roles_user = Column(String, nullable=True)

    # Связи между таблицами UsersPermissions и UsersRoles
    permissions = relationship("UsersPermissions", back_populates="user", uselist=False)
    roles = relationship("UsersRoles", back_populates="user", uselist=True)


class UsersPermissions(Base):
    __tablename__ = "users_permissions"

    id = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_user = Column(Boolean, default=True, server_default=text("true"), nullable=False)
    is_moderator = Column(Boolean, default=False, nullable=False, server_default=text("false"))
    is_super_admin = Column(Boolean, default=False, nullable=False, server_default=text("false"))
    # Связь с таблицей Users
    user = relationship("Users", back_populates="permissions")

    # Связь с таблицей UsersRoles
    roles = relationship("UsersRoles", back_populates="permission", uselist=False)


class UsersRoles(Base):
    __tablename__ = "users_roles"

    id = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    permission_id = Column(Integer, ForeignKey("users_permissions.id"), nullable=True, server_default=text("1"))

    # Связь с таблицей Users
    user = relationship("Users", back_populates="roles")

    # Связь с таблицей UsersPermissions
    permission = relationship("UsersPermissions", back_populates="roles")