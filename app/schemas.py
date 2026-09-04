from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RoomOut(BaseModel):
    id: int
    name: str
    capacity: int
    description: str | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class BookingCreate(BaseModel):
    room_id: int
    title: str
    start_time: datetime
    end_time: datetime

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, end_time, info):
        start_time = info.data.get("start_time")
        if start_time and end_time <= start_time:
            raise ValueError("Время окончания должно быть позже времени начала")
        return end_time


class BookingOut(BaseModel):
    id: int
    room_id: int
    user_id: int
    title: str
    start_time: datetime
    end_time: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NLBookingRequest(BaseModel):
    phrase: str