from dotenv import load_dotenv
from pydantic import BaseSettings
import os

# load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str

    @property
    def DATABASE_URL(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


class Config:
    env_file = ".env"


settings = Settings()
