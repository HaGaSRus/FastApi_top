from fastapi import FastAPI, Query, Depends
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from app.bookings.router import router as router_bookings
from app.hotels.router import router as router_hotels
from app.users.router import router_auth, router_users

from app.pages.router import router as router_pages
from app.images.router import router as router_images

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), "static")


app.include_router(router_users)
app.include_router(router_bookings)
app.include_router(router_hotels)
app.include_router(router_auth)

app.include_router(router_pages)
app.include_router(router_images)

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origns=origins,
    allow_credentials=True,
    allow_method=["GET", "POST", "OPTIONS", "DELETE", "PATCH", "PUT"],
    allow_headers=["Content-Type", "Set-Cookie", "Access-Control-Allow-Headers", "Access-Authorization"],
)

