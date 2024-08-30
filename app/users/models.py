from typing import List
from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database import Base

# Определение таблицы связи между пользователями и ролями (many-to-many)
role_user_association = Table(
    'role_user_association',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
)

class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    firstname: Mapped[str] = mapped_column(String, nullable=False)
    lastname: Mapped[str] = mapped_column(String, nullable=False)

    # Связь many-to-many с ролями через таблицу связи
    roles: Mapped[List['Roles']] = relationship(
        secondary=role_user_association,  # Используем объект таблицы связи
        back_populates='users'
    )

class Roles(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    # Связь many-to-many с пользователями через таблицу связи
    users: Mapped[List[Users]] = relationship(
        secondary=role_user_association,  # Используем объект таблицы связи
        back_populates='roles'
    )

    # Связь one-to-many с правами
    permissions: Mapped[List['Permissions']] = relationship('Permissions', back_populates='role')

class Permissions(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey('roles.id', ondelete='CASCADE'))

    # Связь с таблицей Roles (one-to-many)
    role: Mapped[Roles] = relationship('Roles', back_populates='permissions')