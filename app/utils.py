from fastapi import HTTPException
from fastapi_mail import ConnectionConfig, MessageSchema, FastMail
from sqlalchemy import select
from app.config import settings
from app.database import async_session_maker
from app.logger.logger import logger
from app.users.models import Roles
from aiosmtplib.errors import SMTPException


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


async def send_reset_password_email(email: str, token: str, user_name: str = None):

    site_name = "Горячая линия Тюменской области"
    # Если user_name не передан, используем email
    user_display_name = user_name if user_name else email

    # Формируем тело письма с переменными
    body_content = f"""
{user_display_name},

Запрос на сброс пароля для вашей учетной записи был сделан на {site_name}.

Теперь вы можете войти в систему, щелкнув эту ссылку:

http://hotline.dz72.ru/reset-password?token={token}

Эту ссылку можно использовать только один раз для входа в систему, и она приведет вас на страницу, где вы можете установить свой пароль. Срок ее действия истекает через день, и если она не используется, ничего не произойдет.

-- {site_name}
"""

    message = MessageSchema(
        subject="Запрос на сброс пароля",
        recipients=[email],
        body=body_content,
        subtype="plain"
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
    except SMTPException as smtp_err:
        logger.warning(f"Ошибка SMTP при отправке письма на адрес {email}: {str(smtp_err)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка при отправке письма. Пожалуйста, попробуйте позже.")
    except Exception as e:
        logger.warning(f"Ошибка при отправке письма на адрес {email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Произошла ошибка при отправке письма: {str(e)}")
