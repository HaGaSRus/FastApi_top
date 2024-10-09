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
from aiosmtplib.errors import SMTPException
from fastapi import HTTPException


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


# async def init_permissions():
#     async with async_session_maker() as session:
#         async with session.begin():
#             permissions = [
#                 {"name": "create_user", "role_id": 1},
#                 {"name": "delete_user", "role_id": 2},
#                 {"name": "view_reports", "role_id": 1},
#                 {"name": "view_content", "role_id": 1}
#             ]
#
#             existing_permissions = await session.execute(select(Permissions.name, Permissions.role_id))
#             existing_permissions = {(perm[0], perm[1]) for perm in existing_permissions.fetchall()}
#
#             new_permissions = [perm for perm in permissions if
#                                (perm["name"], perm["role_id"]) not in existing_permissions]
#
#             if new_permissions:
#                 stmt = insert(Permissions).values(new_permissions)
#                 await session.execute(stmt)
#                 await session.commit()


conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=settings.MAIL_TLS,  # Используем MAIL_TLS
    MAIL_SSL_TLS=settings.MAIL_SSL,  # Используем MAIL_SSL
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
    try:
        await fm.send_message(message)
        logger.info(f"Письмо для сброса пароля отправлено на адрес: {email}")
    except SMTPException as smtp_err:
        logger.error(f"Ошибка SMTP при отправке письма на адрес {email}: {str(smtp_err)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка при отправке письма. Пожалуйста, попробуйте позже.")
    except Exception as e:
        logger.error(f"Ошибка при отправке письма на адрес {email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Произошла ошибка при отправке письма: {str(e)}")

    logger.info(f"Время выполнения: {time.time() - start_time} секунд")

#
# SMTP_SERVER = "mail.dz72.ru"
# SMTP_PORT = 25  # Использовать 587 для TLS или 465 для SSL
# SMTP_FROM = "test@dz72.ru"
# SMTP_FROM_NAME = "Hot_Line"
# SMTP_USERNAME = "test"
# SMTP_PASSWORD = "test"
# MAIL_TLS = False  # Изменить на True, если ваш сервер поддерживает TLS
# MAIL_SSL = False  # Изменить на True, если ваш сервер поддерживает SSL
# USE_CREDENTIALS = False  # Использовать ли учетные данные
# VALIDATE_CERTS = True  # Проверять ли сертификаты (если используете SSL/TLS)
#
#
# def send_reset_password_email(email: str, token: str):
#     start_time = time.time()
#     logger.info(f"Отправка письма для сброса пароля на адрес: {email}")
#
#     # Формируем тело письма
#     body_content = f"Нажмите ссылку, чтобы сбросить пароль: http://192.168.188.53:8080/reset-password?token={token}"
#     logger.info(f"Тело письма: {body_content}")
#
#     # Формируем заголовки письма
#     msg = MIMEMultipart()
#     msg['From'] = f"{SMTP_FROM_NAME} <{SMTP_FROM}>"
#     msg['To'] = email
#     msg['Subject'] = "Запрос на сброс пароля"
#     msg.attach(MIMEText(body_content, 'plain'))
#
#     try:
#         # Подключаемся через сокет
#         with socket.create_connection((SMTP_SERVER, SMTP_PORT)) as sock:
#             smtp_conn = smtplib.SMTP()
#             smtp_conn.sock = sock
#             smtp_conn.set_debuglevel(1)
#
#             # Переход на защищённое соединение, если требуется
#             if MAIL_TLS:
#                 smtp_conn.starttls()  # Начинаем TLS-соединение
#             elif MAIL_SSL:
#                 smtp_conn = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)  # Используем SSL-соединение
#
#             # Логинимся на SMTP-сервере, если указаны учетные данные
#             if USE_CREDENTIALS and SMTP_USERNAME and SMTP_PASSWORD:
#                 smtp_conn.login(SMTP_USERNAME, SMTP_PASSWORD)
#
#             # Отправляем письмо
#             smtp_conn.sendmail(SMTP_FROM, [email], msg.as_string())
#             logger.info(f"Письмо для сброса пароля успешно отправлено на адрес: {email}")
#
#     except smtplib.SMTPException as smtp_error:
#         logger.error(f"SMTP ошибка при отправке письма для восстановления пароля на email: {email} - {str(smtp_error)}")
#     except Exception as e:
#         logger.error(f"Ошибка при отправке письма для восстановления пароля на email: {email} - {str(e)}")
#     finally:
#         smtp_conn.quit()
#
#     logger.info(f"Время выполнения: {time.time() - start_time} секунд")