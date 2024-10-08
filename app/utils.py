import time
import smtplib
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from fastapi import APIRouter
from fastapi_mail import ConnectionConfig, MessageSchema, FastMail, MessageType
from sqlalchemy import select, insert
from app.config import settings
from app.database import async_session_maker
from app.logger.logger import logger
from app.users.models import Roles, Permissions
from pydantic import BaseModel, EmailStr
from starlette.responses import JSONResponse
from fastapi_versioning import version


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

            new_permissions = [perm for perm in permissions if
                               (perm["name"], perm["role_id"]) not in existing_permissions]

            if new_permissions:
                stmt = insert(Permissions).values(new_permissions)
                await session.execute(stmt)
                await session.commit()

#
# conf = ConnectionConfig(
#     MAIL_USERNAME=settings.MAIL_USERNAME,
#     MAIL_PASSWORD=settings.MAIL_PASSWORD,
#     MAIL_PORT=settings.MAIL_PORT,
#     MAIL_SERVER=settings.MAIL_SERVER,
#     MAIL_FROM=settings.MAIL_FROM,
#     MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
#     MAIL_STARTTLS=settings.MAIL_TLS,  # Используем MAIL_TLS
#     MAIL_SSL_TLS=settings.MAIL_SSL,  # Используем MAIL_SSL
#     MAIL_DEBUG=settings.MAIL_DEBUG,
#     SUPPRESS_SEND=settings.SUPPRESS_SEND,
#     USE_CREDENTIALS=settings.USE_CREDENTIALS,
#     VALIDATE_CERTS=settings.VALIDATE_CERTS,
#     TIMEOUT=settings.TIMEOUT
# )
#
#
# async def send_reset_password_email(email: str, token: str):
#     start_time = time.time()
#     logger.info(f"Отправка письма для сброса пароля на адрес: {email}")
#
#     body_content = f"Нажмите ссылку, чтобы сбросить пароль: http://192.168.188.53:8080/reset-password?token={token}"
#     logger.info(f"Тело письма: {body_content}")
#
#     message = MessageSchema(
#         subject="Запрос на сброс пароля",
#         recipients=[email],
#         body=body_content,
#         subtype="html"
#     )
#
#     fm = FastMail(conf)
#     await fm.send_message(message)
#     logger.info(f"Письмо для сброса пароля отправлено на адрес: {email}")
#     logger.info(f"Время выполнения: {time.time() - start_time} секунд")


# Конфигурация SMTP-сервера
SMTP_SERVER = "192.168.0.77:8888"
SMTP_PORT = 25
SMTP_FROM = settings.MAIL_FROM
SMTP_FROM_NAME = settings.MAIL_FROM_NAME
SMTP_USERNAME = settings.MAIL_USERNAME
SMTP_PASSWORD = settings.MAIL_PASSWORD


# Функция для отправки письма с использованием сокета
def send_reset_password_email(email: str, token: str):
    start_time = time.time()
    logger.info(f"Отправка письма для сброса пароля на адрес: {email}")

    # Формируем тело письма
    body_content = f"Нажмите ссылку, чтобы сбросить пароль: http://192.168.188.53:8080/reset-password?token={token}"
    logger.info(f"Тело письма: {body_content}")

    # Формируем заголовки письма (subject, from, to, etc.)
    msg = MIMEMultipart()
    msg['From'] = f"{SMTP_FROM_NAME} <{SMTP_FROM}>"
    msg['To'] = email
    msg['Subject'] = "Запрос на сброс пароля"

    # Добавляем текст письма
    msg.attach(MIMEText(body_content, 'html'))

    try:
        # Подключаемся через сокет
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((SMTP_SERVER, SMTP_PORT))

        # Устанавливаем SMTP-соединение через сокет
        smtp_conn = smtplib.SMTP()
        smtp_conn.sock = sock  # Привязываем сокет к SMTP соединению
        smtp_conn.set_debuglevel(1)  # Включаем режим отладки (если нужно)

        # Логинимся на SMTP-сервере, если требуются учетные данные
        if SMTP_USERNAME and SMTP_PASSWORD:
            smtp_conn.login(SMTP_USERNAME, SMTP_PASSWORD)

        # Отправляем письмо
        smtp_conn.sendmail(SMTP_FROM, [email], msg.as_string())

        # Закрываем соединение
        smtp_conn.quit()
        logger.info(f"Письмо для сброса пароля успешно отправлено на адрес: {email}")
    except Exception as e:
        logger.error(f"Ошибка при отправке письма для восстановления пароля на email: {email} - {str(e)}")
    finally:
        # Закрываем сокет
        sock.close()

    logger.info(f"Время выполнения: {time.time() - start_time} секунд")