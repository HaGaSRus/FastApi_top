from contextlib import asynccontextmanager
from urllib.request import Request
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from fastapi_versioning import VersionedFastAPI
import uvicorn
import time
from typing import AsyncIterator

from app.logger.middleware import LoggingMiddleware
from app.admin.pagination import router_pagination
from app.users.router import router_users
from app.auth.router import router_auth
from app.admin.router import router_admin
from app.utils import init_permissions, init_roles
from app.logger.logger import logger


# Определяем функцию жизненного цикла с использованием asynccontextmanager
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Код, выполняемый при запуске приложения
    await init_roles()
    await init_permissions()
    yield
    # Код, выполняемый при завершении работы (если требуется)

# Создаем приложение FastAPI с контекстом жизненного цикла
app = FastAPI(lifespan=lifespan)


app.include_router(router_users)
app.include_router(router_auth)
app.include_router(router_admin)
app.include_router(router_pagination)

app = VersionedFastAPI(app,
                       version_format='{major}',
                       prefix_format='/v{major}')

origins = [
    "http://localhost:8080",
    "http://192.168.188.53:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info("Request handling time", extra={
        "process_time": round(process_time, 4)
    })
    return response



if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
