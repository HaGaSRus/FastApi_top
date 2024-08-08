from fastapi import APIRouter

from dao import BookingDAO

router = APIRouter(
    prefix="/bookings",
    tags=["Бронирование"],
)


@router.get("")
async def get_bookings():
    # result = BookingDAO.find_all()
    # return result
    pass
