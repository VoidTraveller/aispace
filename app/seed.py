from app.database import SessionLocal
from app.models import Room

SAMPLE_ROOMS = [
    {"name": "Маленькая", "capacity": 4, "description": "Для быстрых созвонов"},
    {"name": "Большая переговорка", "capacity": 12, "description": "Основная комната для встреч"},
    {"name": "Тихая комната", "capacity": 2, "description": "Для звонков один на один"},
]


def seed_rooms():
    db = SessionLocal()
    try:
        if db.query(Room).count() == 0:
            for room_data in SAMPLE_ROOMS:
                db.add(Room(**room_data, is_active=True))
            db.commit()
            print(f"Seeded {len(SAMPLE_ROOMS)} rooms")
        else:
            print("Rooms already exist, skipping seed")
    finally:
        db.close()


if __name__ == "__main__":
    seed_rooms()