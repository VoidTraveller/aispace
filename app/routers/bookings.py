from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Booking, Room, User
from app.schemas import BookingOut, BookingCreate, NLBookingRequest, NLBookingResult

from app.deepseek_client import parse_booking_phrase, DeepSeekParseError

router = APIRouter(prefix="/bookings", tags=["bookings"])

@router.get("", response_model=list[BookingOut])
def list_bookings(room_id: int | None = None, on_date: date | None = None, db: Session = Depends(get_db)):
    query = db.query(Booking).options(joinedload(Booking.room), joinedload(Booking.user))
    if room_id is not None:
        query = query.filter(Booking.room_id == room_id)
    if on_date is not None:
        query = query.filter(func.date(Booking.start_time) == on_date)
    return query.all()



def create_booking_or_409(db: Session, room_id: int, user_id: int, title: str, start_time, end_time) -> Booking:
    if start_time < datetime.now():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Нельзя создать бронь в прошлом")

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

    # exact match first; ILIKE is just a fallback in case DeepSeek doesn't follow instructions
    room = db.query(Room).filter(Room.name == room_query).first()
    if room is None:
        room = db.query(Room).filter(Room.name.ilike(f"%{room_query}%")).first()
    if room is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Комната с названием «{room_query}» не найдена")
    return room


@router.post("/nl", status_code=status.HTTP_201_CREATED)
def create_booking_nl(
        payload: NLBookingRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    room_names = [r.name for r in db.query(Room).filter(Room.is_active == True).all()]

    try:
        parsed = parse_booking_phrase(payload.phrase, room_names)
    except DeepSeekParseError:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Не удалось обработать запрос через ИИ-сервис. Пожалуйста, создайте бронь вручную.",
        )

    room_query = parsed.get("room_query")
    date_str = parsed.get("date")
    end_date_str = parsed.get("end_date") or date_str
    start_time_str = parsed.get("start_time")
    duration = parsed.get("duration_minutes")
    title = parsed.get("title") or "Бронь"

    if not all([room_query, date_str, start_time_str, duration]):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "Не удалось извлечь все необходимые данные бронирования из фразы")

    try:
        start_time_of_day = datetime.strptime(start_time_str, "%H:%M").time()
        first_day = datetime.fromisoformat(date_str).date()
        last_day = datetime.fromisoformat(end_date_str).date()
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "ИИ-сервис вернул нераспознаваемую дату или время")

    if not isinstance(duration, int) or duration <= 0 or duration > 480:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Длительность брони должна быть от 1 минуты до 8 часов")

    room = resolve_room(db, room_query)

    if last_day < first_day:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Дата окончания раньше даты начала")

    all_days = []
    d = first_day
    while d <= last_day:
        all_days.append(d)
        d += timedelta(days=1)

    # single day -- identical shape/status to before multi-day support existed
    if len(all_days) == 1:
        start_dt = datetime.combine(first_day, start_time_of_day)
        end_dt = start_dt + timedelta(minutes=duration)
        return create_booking_or_409(db, room.id, current_user.id, title, start_dt, end_dt)

    # multi-day range: one booking per weekday, same semantics as the manual booking form
    days = [d for d in all_days if d.weekday() < 5]
    skipped = [d.isoformat() for d in all_days if d.weekday() >= 5]

    created = []
    failed = []
    for d in days:
        start_dt = datetime.combine(d, start_time_of_day)
        end_dt = start_dt + timedelta(minutes=duration)
        try:
            created.append(create_booking_or_409(db, room.id, current_user.id, title, start_dt, end_dt))
        except HTTPException as e:
            failed.append(f"{d.isoformat()}: {e.detail}")

    if not created:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "; ".join(failed) or "Не удалось создать ни одной брони")

    result = NLBookingResult(
        created=[BookingOut.model_validate(b) for b in created],
        skipped_weekends=skipped,
        failed=failed,
    )
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=jsonable_encoder(result))
