from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Room, User
from app.schemas import RoomOut, RoomCreate, RoomUpdate

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("", response_model=list[RoomOut])
def list_rooms(db: Session = Depends(get_db)):
    return db.query(Room).all()


@router.post("", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
def create_room(
    payload: RoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if db.query(Room).filter(Room.name == payload.name).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Комната с таким названием уже существует")

    room = Room(name=payload.name, capacity=payload.capacity, description=payload.description, is_active=True)
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@router.patch("/{room_id}", response_model=RoomOut)
def update_room_status(
    room_id: int,
    payload: RoomUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if room is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Комната не найдена")

    room.is_active = payload.is_active
    db.commit()
    db.refresh(room)
    return room
