from fastapi import APIRouter, Request
from app.bookings.dao import BookingDAO
from app.bookings.schemas import SBooking

router = APIRouter(
    prefix="/bookings",
    tags=["Бронирование"],
)


@router.get("")
async def get_bookings(user):  # -> list[SBooking]:
    return await BookingDAO.find_all()
