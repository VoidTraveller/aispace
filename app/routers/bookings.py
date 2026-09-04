from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Booking, Room, User
from app.schemas import BookingOut, BookingCreate, NLBookingRequest

from app.deepseek_client import parse_booking_phrase, DeepSeekParseError

router = APIRouter(prefix="/bookings", tags=["bookings"])

@router.get("", response_model=list[BookingOut])
def list_bookings(room_id: int | None = None, on_date: date | None = None, db: Session = Depends(get_db)):
    query = db.query(Booking)
    if room_id is not None:
        query = query.filter(Booking.room_id == room_id)
    if on_date is not None:
        query = query.filter(func.date(Booking.start_time) == on_date)
    return query.all()



def create_booking_or_409(db: Session, room_id: int, user_id: int, title: str, start_time, end_time) -> Booking:
    room = db.query(Room).filter(Room.id == room_id).first()
    if room is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Комната не найдена")
    if not room.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "Комната недоступна для бронирования")

    conflict = (
        db.query(Booking)
        .filter(Booking.room_id == room_id)
        .filter(Booking.start_time < end_time)
        .filter(Booking.end_time > start_time)
        .first()
    )
    if conflict is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Комната уже забронирована на этот промежуток времени")

    booking = Booking(room_id=room_id, user_id=user_id, title=title, start_time=start_time, end_time=end_time)
    db.add(booking)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Комната уже забронирована на этот промежуток времени")

    db.refresh(booking)
    return booking


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_booking_or_409(
        db, payload.room_id, current_user.id, payload.title, payload.start_time, payload.end_time
    )


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Бронь не найдена")
    if booking.user_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Вы можете отменять только свои брони")

    db.delete(booking)
    db.commit()

def resolve_room(db: Session, room_query: str | None) -> Room:
    if not room_query:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Не удалось определить, какая комната запрошена")
    room = db.query(Room).filter(Room.name.ilike(f"%{room_query}%")).first()
    if room is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Комната с названием «{room_query}» не найдена")
    return room


@router.post("/nl", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking_nl(
        payload: NLBookingRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    try:
        parsed = parse_booking_phrase(payload.phrase)
    except DeepSeekParseError:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Не удалось обработать запрос через ИИ-сервис. Пожалуйста, создайте бронь вручную.",
        )

    room_query = parsed.get("room_query")
    date_str = parsed.get("date")
    start_time_str = parsed.get("start_time")
    duration = parsed.get("duration_minutes")
    title = parsed.get("title") or "Бронь"

    if not all([room_query, date_str, start_time_str, duration]):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "Не удалось извлечь все необходимые данные бронирования из фразы")

    try:
        start_dt = datetime.fromisoformat(f"{date_str}T{start_time_str}:00")
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "ИИ-сервис вернул нераспознаваемую дату или время")

    if not isinstance(duration, int) or duration <= 0 or duration > 480:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Длительность брони должна быть от 1 минуты до 8 часов")

    end_dt = start_dt + timedelta(minutes=duration)
    room = resolve_room(db, room_query)

    return create_booking_or_409(db, room.id, current_user.id, title, start_dt, end_dt)
