from fastapi import FastAPI, Query, Depends
from typing import Optional
from datetime import date
from pydantic import BaseModel

from app.bookings.router import router as router_bookings

app = FastAPI()

app.include_router(router_bookings)


class HotelsSearchArgs:
    def __init__(
        self,
        location,
        date_form: date,
        date_to: date,
        has_spa: Optional[bool] = None,
        stars: Optional[int] = Query(None, ge=1, le=5),
    ):
        self.location = location
        self.date_form = date_form
        self.date_to = date_to
        self.has_spa = has_spa
        self.stars = stars


@app.get("/hotels")
def get_hotels(
    search_args: HotelsSearchArgs = Depends(),
):
    return search_args


class SBooking(BaseModel):
    room_id: int
    date_form: date
    date_to: date


@app.post("/booking")
def add_booking(booking: SBooking):
    return booking
