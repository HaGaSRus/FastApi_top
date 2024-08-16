from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
import uvicorn

from app.admin.views import UserAdmin
from app.database import engine
from app.users.router import router_auth, router_users
from app.utils import init_permissions, init_roles
from sqladmin import Admin


app = FastAPI()
admin = Admin(app, engine)

admin.add_view(UserAdmin)

app.include_router(router_users)
app.include_router(router_auth)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    await init_roles()
    await init_permissions()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
