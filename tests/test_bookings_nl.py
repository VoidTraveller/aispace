from unittest.mock import patch

from app.deepseek_client import DeepSeekParseError
from conftest import register_and_login


def test_nl_booking_success(client, room):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    fake_result = {
        "room_query": "Test Room", "date": "2026-09-10",
        "start_time": "14:00", "duration_minutes": 60, "title": "Standup",
    }
    with patch("app.routers.bookings.parse_booking_phrase", return_value=fake_result):
        response = client.post("/bookings/nl", headers=headers, json={"phrase": "anything"})

    assert response.status_code == 201
    body = response.json()
    assert body["room_id"] == room
    assert body["start_time"] == "2026-09-10T14:00:00"
    assert body["end_time"] == "2026-09-10T15:00:00"


def test_nl_booking_deepseek_failure_returns_502(client, room):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.routers.bookings.parse_booking_phrase", side_effect=DeepSeekParseError("boom")):
        response = client.post("/bookings/nl", headers=headers, json={"phrase": "anything"})

    assert response.status_code == 502


def test_nl_booking_missing_fields_returns_422(client, room):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    incomplete = {"room_query": None, "date": "2026-09-10", "start_time": "14:00", "duration_minutes": 60, "title": "x"}
    with patch("app.routers.bookings.parse_booking_phrase", return_value=incomplete):
        response = client.post("/bookings/nl", headers=headers, json={"phrase": "anything"})

    assert response.status_code == 422


def test_nl_booking_invalid_duration_returns_422(client, room):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    bad_duration = {"room_query": "Test Room", "date": "2026-09-10", "start_time": "14:00", "duration_minutes": 10000, "title": "x"}
    with patch("app.routers.bookings.parse_booking_phrase", return_value=bad_duration):
        response = client.post("/bookings/nl", headers=headers, json={"phrase": "anything"})

    assert response.status_code == 422


def test_nl_booking_room_not_found_returns_404(client):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    no_match = {"room_query": "Nonexistent Room XYZ", "date": "2026-09-10", "start_time": "14:00", "duration_minutes": 60, "title": "x"}
    with patch("app.routers.bookings.parse_booking_phrase", return_value=no_match):
        response = client.post("/bookings/nl", headers=headers, json={"phrase": "anything"})

    assert response.status_code == 404


def test_nl_booking_requires_auth(client):
    response = client.post("/bookings/nl", json={"phrase": "anything"})
    assert response.status_code == 401
