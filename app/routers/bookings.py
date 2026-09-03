from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Booking, Room, User
from app.schemas import BookingOut, BookingCreate

router = APIRouter(prefix="/bookings", tags=["bookings"])

@router.get("", response_model=list[BookingOut])
def list_bookings(room_id: int | None = None, on_date: date | None = None, db: Session = Depends(get_db)):
    query = db.query(Booking)
    if room_id is not None:
        query = query.filter(Booking.room_id == room_id)
    if on_date is not None:
        query = query.filter(func.date(Booking.start_time) == on_date)
    return query.all()



@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room = db.query(Room).filter(Room.id == payload.room_id).first()
    if room is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found")
    if not room.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "Room is not available for booking")

    conflict = (
        db.query(Booking)
        .filter(Booking.room_id == payload.room_id)
        .filter(Booking.start_time < payload.end_time)
        .filter(Booking.end_time > payload.start_time)
        .first()
    )
    if conflict is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Room is already booked for this time range")

    booking = Booking(
        room_id=payload.room_id,
        user_id=current_user.id,
        title=payload.title,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    db.add(booking)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Room is already booked for this time range")

    db.refresh(booking)
    return booking


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    if booking.user_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only cancel your own bookings")

    db.delete(booking)
    db.commit()