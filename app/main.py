import time

import uvicorn
from fastapi import FastAPI, Request
from sqladmin import Admin
from starlette.middleware.cors import CORSMiddleware
from fastapi_versioning import VersionedFastAPI


from app.admin.views import UserAdmin
from app.database import engine
from app.users.router import router_auth, router_users
from app.utils import init_permissions, init_roles
from app.logger import logger

app = FastAPI()


app.include_router(router_users)
app.include_router(router_auth)

app = VersionedFastAPI(app,
                       version_format='{major}',
                       prefix_format='/v{major}')



origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info("Request handling time", extra={
        "process_time": round(process_time, 4)
    })
    return response


admin = Admin(app, engine)
admin.add_view(UserAdmin)


@app.on_event("startup")
async def on_startup():
    await init_roles()
    await init_permissions()




if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
