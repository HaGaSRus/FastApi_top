import time
from fastapi_mail import ConnectionConfig, MessageSchema, FastMail
from sqlalchemy import select, insert
from app.config import settings
from app.database import async_session_maker
from app.logger import logger
from app.users.models import Roles, Permissions

async def init_roles():
    async with async_session_maker() as session:
        roles = ["user", "admin", "moderator"]

        for role_name in roles:
            existing_role = await session.execute(select(Roles).where(Roles.name == role_name))
            existing_role = existing_role.scalar_one_or_none()

            if not existing_role:
                new_role = Roles(name=role_name)
                session.add(new_role)

        await session.commit()

async def init_permissions():
    async with async_session_maker() as session:
        async with session.begin():
            permissions = [
                {"name": "create_user", "role_id": 1},
                {"name": "delete_user", "role_id": 2},
                {"name": "view_reports", "role_id": 1},
                {"name": "view_content", "role_id": 1}
            ]

            existing_permissions = await session.execute(select(Permissions.name, Permissions.role_id))
            existing_permissions = {(perm[0], perm[1]) for perm in existing_permissions.fetchall()}

            new_permissions = [perm for perm in permissions if (perm["name"], perm["role_id"]) not in existing_permissions]

            if new_permissions:
                stmt = insert(Permissions).values(new_permissions)
                await session.execute(stmt)
                await session.commit()

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    MAIL_DEBUG=settings.MAIL_DEBUG,
    SUPPRESS_SEND=settings.SUPPRESS_SEND,
    USE_CREDENTIALS=settings.USE_CREDENTIALS,
    VALIDATE_CERTS=settings.VALIDATE_CERTS,
    TIMEOUT=settings.TIMEOUT
)

async def send_reset_password_email(email: str, token: str):
    start_time = time.time()
    logger.info(f"Отправка письма для сброса пароля на адрес: {email}")

    body_content = f"Нажмите ссылку, чтобы сбросить пароль: http://192.168.188.53:8080/reset-password?token={token}"
    logger.info(f"Тело письма: {body_content}")

    message = MessageSchema(
        subject="Запрос на сброс пароля",
        recipients=[email],
        body=body_content,
        subtype="plain"
    )

    fm = FastMail(conf)
    await fm.send_message(message)
    logger.info(f"Письмо для сброса пароля отправлено на адрес: {email}")
    logger.info(f"Время выполнения: {time.time() - start_time} секунд")
