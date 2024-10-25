from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi_versioning import VersionedFastAPI
import uvicorn
import time
from typing import AsyncIterator
from fastapi.responses import JSONResponse
from app.logger.middleware import LoggingMiddleware
from app.admin.pagination_and_filtration import router_pagination, router_filter
from app.users.router import router_users
from app.auth.router import router_auth
from app.admin.router import router_admin
from app.analytics.router import router_analytics
from app.questions.router_question import router_question
from app.questions.router_categories import router_categories
from app.utils import init_roles
from app.logger.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await init_roles()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(router_users)
app.include_router(router_auth)
app.include_router(router_admin)
app.include_router(router_pagination)
app.include_router(router_filter)
app.include_router(router_question)
app.include_router(router_categories)
app.include_router(router_analytics)

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
    allow_methods=["GET", "POST", "OPTIONS"],
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


@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except HTTPException as ex:
        return JSONResponse(
            status_code=ex.status_code,
            content={"detail": ex.detail}
        )
    except Exception as ex:
        logger.warning(f"Непредвиденная ошибка: {ex}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Внутренняя ошибка сервера"}
        )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)

