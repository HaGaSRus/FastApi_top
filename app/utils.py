from sqlalchemy import select, insert

from app.database import async_session_maker
from app.users.models import Roles, Permissions


async def init_roles():
    async with async_session_maker() as session:
        roles = ["user", "admin", "moderator"]  # Список ролей, которые нужно добавить

        for role_name in roles:
            # Проверка существующих ролей
            existing_role = await session.execute(select(Roles).where(Roles.name == role_name))
            existing_role = existing_role.scalar_one_or_none()

            if not existing_role:
                new_role = Roles(name=role_name)
                session.add(new_role)

        await session.commit()

async def init_permissions():
    async with async_session_maker() as session:
        # Начало транзакции
        async with session.begin():
            permissions = [
                {"name": "create_user", "role_id": 1},  # Укажите реальный role_id
                {"name": "delete_user", "role_id": 1},
                {"name": "view_reports", "role_id": 1},
                {"name": "view_content", "role_id": 2}  # Укажите реальный role_id
            ]

            # Проверка существующих разрешений
            existing_permissions = await session.execute(select(Permissions.name, Permissions.role_id))
            existing_permissions = {(perm[0], perm[1]) for perm in existing_permissions.fetchall()}

            # Фильтрация новых разрешений
            new_permissions = [perm for perm in permissions if (perm["name"], perm["role_id"]) not in existing_permissions]

            if new_permissions:
                # Вставка новых разрешений
                stmt = insert(Permissions).values(new_permissions)
                await session.execute(stmt)
                await session.commit()