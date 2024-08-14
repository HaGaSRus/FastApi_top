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
    is_superuser = Column(String, default=False)
    roles = Column(String, default="user")

    # Связи между таблицами UsersPermissions и UsersRoles
    permissions = relationship("UsersPermissions", back_populates="user", uselist=False)
    roles = relationship("UsersRoles", back_populates="user", uselist=False)


class UsersPermissions(Base):
    __tablename__ = "users_permissions"

    id = Column(Integer, primary_key=True, nullable=False)
    user_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    is_user = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    is_moderator = mapped_column(Boolean, default=False, nullable=False, server_default=text("false"))
    is_super_admin = mapped_column(Boolean, default=False, nullable=False, server_default=text("false"))

    # Связь с таблицей Users
    user = relationship("Users", back_populates="users_permissions")

    # Связь с таблицей UsersRoles
    roles = relationship("UsersRoles", back_populates="permission", uselist=False)


class UsersRoles(Base):
    __tablename__ = "users_roles"

    id = Column(Integer, primary_key=True, nullable=False)
    user_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    permission_id = mapped_column(Integer, ForeignKey("users_permissions.id"), nullable=False)

    user = relationship("Users", back_populates="roles")
    permission = relationship("UsersPermissions", back_populates="roles")

    # Связь с таблицей Users
    user = relationship("Users", back_populates="roles")

    # Связь с таблицей UsersPermissions
    permission = relationship("UsersPermissions", back_populates="roles")