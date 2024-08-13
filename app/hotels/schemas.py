from typing import List

from pydantic import BaseModel

class SHotel(BaseModel):
    id: int
    name: str
    locations: str
    services: List[str]
    room_quantity: int
    image_id: int

    class Config:
        orm_mode = True

class SHotelInfo(SHotel):
    rooms_left: int

    class Config:
        orm_mode = True
