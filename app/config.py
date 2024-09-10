from typing import Literal, Optional
from pydantic_settings import BaseSettings
from pydantic import EmailStr, conint
from aiosmtplib.api import DEFAULT_TIMEOUT

class Settings(BaseSettings):
    MODE: Literal["DEV", "TEST", "PROD"]
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str

    @property
    def DATABASE_URL(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    SECRET_KEY: str
    ALGORITHM: str

    # Настройки почты
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_FROM: EmailStr
    MAIL_FROM_NAME: Optional[str] = "Hot_Line"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False  # Убедитесь, что это правильное имя параметра
    MAIL_DEBUG: conint(gt=-1, lt=2) = 0
    SUPPRESS_SEND: conint(gt=-1, lt=2) = 0
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True
    TIMEOUT: int = DEFAULT_TIMEOUT

    class Config:
        env_file = ".env"
        from_attributes = True

settings = Settings()
