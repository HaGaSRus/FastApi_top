import uvicorn
from fastapi import FastAPI, Query, Depends
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware


from app.users.router import router_auth, router_users


app = FastAPI()


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



# if __name__ == "__main__":
#     uvicorn.run(app, port=8000)