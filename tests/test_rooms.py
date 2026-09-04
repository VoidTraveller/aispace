from sqlalchemy.exc import IntegrityError

from conftest import register_and_login, future_date, TestSessionLocal
from app.models import Room


def test_room_name_unique_at_db_level():
    """The app-level duplicate-name check alone doesn't cover a race between two
    concurrent requests; this proves the DB constraint backs it up regardless."""
    db = TestSessionLocal()
    db.add(Room(name="Крыша", capacity=6))
    db.commit()

    db.add(Room(name="Крыша", capacity=8))
    try:
        db.commit()
        assert False, "expected IntegrityError"
    except IntegrityError:
        db.rollback()
    db.close()


def test_create_room_success(client):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/rooms", headers=headers, json={
        "name": "Крыша", "capacity": 6, "description": "с видом на город",
    })
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Крыша"
    assert body["is_active"] is True


def test_create_room_duplicate_name_rejected(client):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/rooms", headers=headers, json={"name": "Крыша", "capacity": 6})
    response = client.post("/rooms", headers=headers, json={"name": "Крыша", "capacity": 8})
    assert response.status_code == 409


def test_create_room_requires_auth(client):
    response = client.post("/rooms", json={"name": "Крыша", "capacity": 6})
    assert response.status_code == 401


def test_update_nonexistent_room_returns_404(client):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.patch("/rooms/999999", headers=headers, json={"is_active": False})
    assert response.status_code == 404


def test_update_room_status_requires_auth(client, room):
    response = client.patch(f"/rooms/{room}", json={"is_active": False})
    assert response.status_code == 401


def test_deactivated_room_rejects_new_bookings(client, room):
    """End-to-end: deactivate a room through the real PATCH endpoint (not the
    inactive_room fixture), then confirm booking it is rejected -- proves the
    toggle itself, not just a pre-seeded inactive flag, actually takes effect."""
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    day = future_date()

    still_active = client.post("/bookings", headers=headers, json={
        "room_id": room, "title": "Before deactivation", "start_time": f"{day}T09:00:00", "end_time": f"{day}T10:00:00",
    })
    assert still_active.status_code == 201

    patch_response = client.patch(f"/rooms/{room}", headers=headers, json={"is_active": False})
    assert patch_response.status_code == 200
    assert patch_response.json()["is_active"] is False

    rejected = client.post("/bookings", headers=headers, json={
        "room_id": room, "title": "After deactivation", "start_time": f"{day}T11:00:00", "end_time": f"{day}T12:00:00",
    })
    assert rejected.status_code == 409

    reactivated = client.patch(f"/rooms/{room}", headers=headers, json={"is_active": True})
    assert reactivated.status_code == 200

    works_again = client.post("/bookings", headers=headers, json={
        "room_id": room, "title": "After reactivation", "start_time": f"{day}T13:00:00", "end_time": f"{day}T14:00:00",
    })
    assert works_again.status_code == 201


def test_list_rooms_returns_created_room(client, room):
    response = client.get("/rooms")
    assert response.status_code == 200
    rooms = response.json()
    assert len(rooms) == 1
    assert rooms[0]["id"] == room
    assert rooms[0]["is_active"] is True


def test_list_rooms_empty_when_none_exist(client):
    response = client.get("/rooms")
    assert response.status_code == 200
    assert response.json() == []
