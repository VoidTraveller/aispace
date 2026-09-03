from conftest import register_and_login


def test_booking_created_successfully(client, room):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/bookings", headers=headers, json={
        "room_id": room, "title": "Standup", "start_time": "2026-09-10T14:00:00", "end_time": "2026-09-10T15:00:00",
    })
    assert response.status_code == 201
    body = response.json()
    assert body["room_id"] == room
    assert body["title"] == "Standup"


def test_booking_overlap_rejected(client, room):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post("/bookings", headers=headers, json={
        "room_id": room, "title": "First", "start_time": "2026-09-10T14:00:00", "end_time": "2026-09-10T15:00:00",
    })
    assert first.status_code == 201

    overlapping = client.post("/bookings", headers=headers, json={
        "room_id": room, "title": "Conflict", "start_time": "2026-09-10T14:30:00", "end_time": "2026-09-10T15:30:00",
    })
    assert overlapping.status_code == 409


def test_booking_back_to_back_allowed(client, room):
    """Proves the tsrange half-open [start, end) semantics: a meeting ending exactly
    when another starts is NOT a conflict -- documented in README as intended behavior."""
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post("/bookings", headers=headers, json={
        "room_id": room, "title": "First", "start_time": "2026-09-10T14:00:00", "end_time": "2026-09-10T15:00:00",
    })
    assert first.status_code == 201

    back_to_back = client.post("/bookings", headers=headers, json={
        "room_id": room, "title": "Next", "start_time": "2026-09-10T15:00:00", "end_time": "2026-09-10T16:00:00",
    })
    assert back_to_back.status_code == 201


def test_booking_invalid_time_range_rejected(client, room):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/bookings", headers=headers, json={
        "room_id": room, "title": "Backwards", "start_time": "2026-09-10T15:00:00", "end_time": "2026-09-10T14:00:00",
    })
    assert response.status_code == 422


def test_booking_requires_auth(client, room):
    response = client.post("/bookings", json={
        "room_id": room, "title": "NoAuth", "start_time": "2026-09-10T14:00:00", "end_time": "2026-09-10T15:00:00",
    })
    assert response.status_code == 401


def test_booking_nonexistent_room_returns_404(client):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/bookings", headers=headers, json={
        "room_id": 999999, "title": "Ghost room", "start_time": "2026-09-10T14:00:00", "end_time": "2026-09-10T15:00:00",
    })
    assert response.status_code == 404


def test_booking_inactive_room_rejected(client, inactive_room):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/bookings", headers=headers, json={
        "room_id": inactive_room, "title": "Should fail", "start_time": "2026-09-10T14:00:00", "end_time": "2026-09-10T15:00:00",
    })
    assert response.status_code == 409


def test_delete_booking_ownership(client, room):
    token_a = register_and_login(client, email="ownerA@test.com")
    token_b = register_and_login(client, email="ownerB@test.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    created = client.post("/bookings", headers=headers_a, json={
        "room_id": room, "title": "A's booking", "start_time": "2026-09-10T14:00:00", "end_time": "2026-09-10T15:00:00",
    })
    booking_id = created.json()["id"]

    forbidden = client.delete(f"/bookings/{booking_id}", headers=headers_b)
    assert forbidden.status_code == 403

    success = client.delete(f"/bookings/{booking_id}", headers=headers_a)
    assert success.status_code == 204

    already_gone = client.delete(f"/bookings/{booking_id}", headers=headers_a)
    assert already_gone.status_code == 404


def test_delete_booking_requires_auth(client, room):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post("/bookings", headers=headers, json={
        "room_id": room, "title": "Needs auth to delete", "start_time": "2026-09-10T14:00:00", "end_time": "2026-09-10T15:00:00",
    })
    booking_id = created.json()["id"]

    response = client.delete(f"/bookings/{booking_id}")
    assert response.status_code == 401
