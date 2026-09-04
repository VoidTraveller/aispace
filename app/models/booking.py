from datetime import datetime

from sqlalchemy import DateTime,ForeignKey, String, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ExcludeConstraint

from app.database import Base

class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    room: Mapped["Room"] = relationship(back_populates="bookings")
    user: Mapped["User"] = relationship(back_populates="bookings")

    @property
    def room_name(self) -> str:
        return self.room.name

    @property
    def user_name(self) -> str:
        return f"{self.user.first_name} {self.user.last_name}"

    __table_args__ = (
        CheckConstraint("end_time > start_time", name="check_end_after_start"),
        ExcludeConstraint(
            (room_id, "="),
            (func.tsrange(start_time, end_time), "&&"),
            using="gist",
            name="exclude_overlapping_bookings",
        ),
    )