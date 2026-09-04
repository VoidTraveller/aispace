from datetime import datetime, timedelta
from unittest.mock import patch

from app.deepseek_client import DeepSeekParseError
from conftest import register_and_login, future_date


def test_nl_booking_success(client, room):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    day = future_date()

    fake_result = {
        "room_query": "Test Room", "date": day,
        "start_time": "14:00", "duration_minutes": 60, "title": "Standup",
    }
    with patch("app.routers.bookings.parse_booking_phrase", return_value=fake_result):
        response = client.post("/bookings/nl", headers=headers, json={"phrase": "anything"})

    assert response.status_code == 201
    body = response.json()
    assert body["room_id"] == room
    assert body["start_time"] == f"{day}T14:00:00"
    assert body["end_time"] == f"{day}T15:00:00"


def test_nl_booking_inactive_room_rejected(client, inactive_room):
    """Defense-in-depth: DeepSeek returning an inactive room's exact name is still rejected."""
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    day = future_date()

    fake_result = {
        "room_query": "Test Room", "date": day,
        "start_time": "14:00", "duration_minutes": 60, "title": "Standup",
    }
    with patch("app.routers.bookings.parse_booking_phrase", return_value=fake_result):
        response = client.post("/bookings/nl", headers=headers, json={"phrase": "anything"})

    assert response.status_code == 409


def test_nl_excludes_inactive_rooms_from_deepseek_prompt(client, room):
    """Primary defense: inactive rooms are never offered to DeepSeek as an option at all."""
    from conftest import TestSessionLocal
    from app.models import Room

    db = TestSessionLocal()
    db.add(Room(name="Retired Room", capacity=2, is_active=False))
    db.commit()
    db.close()

    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    day = future_date()

    fake_result = {
        "room_query": "Test Room", "date": day,
        "start_time": "14:00", "duration_minutes": 60, "title": "Standup",
    }
    with patch("app.routers.bookings.parse_booking_phrase", return_value=fake_result) as mock_parse:
        client.post("/bookings/nl", headers=headers, json={"phrase": "anything"})

    called_room_names = mock_parse.call_args[0][1]
    assert "Retired Room" not in called_room_names
    assert "Test Room" in called_room_names


def test_nl_booking_deepseek_failure_returns_502(client, room):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.routers.bookings.parse_booking_phrase", side_effect=DeepSeekParseError("boom")):
        response = client.post("/bookings/nl", headers=headers, json={"phrase": "anything"})

    assert response.status_code == 502


def test_nl_booking_missing_fields_returns_422(client, room):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    incomplete = {"room_query": None, "date": future_date(), "start_time": "14:00", "duration_minutes": 60, "title": "x"}
    with patch("app.routers.bookings.parse_booking_phrase", return_value=incomplete):
        response = client.post("/bookings/nl", headers=headers, json={"phrase": "anything"})

    assert response.status_code == 422


def test_nl_booking_invalid_duration_returns_422(client, room):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    bad_duration = {"room_query": "Test Room", "date": future_date(), "start_time": "14:00", "duration_minutes": 10000, "title": "x"}
    with patch("app.routers.bookings.parse_booking_phrase", return_value=bad_duration):
        response = client.post("/bookings/nl", headers=headers, json={"phrase": "anything"})

    assert response.status_code == 422


def test_nl_booking_room_not_found_returns_404(client):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    no_match = {"room_query": "Nonexistent Room XYZ", "date": future_date(), "start_time": "14:00", "duration_minutes": 60, "title": "x"}
    with patch("app.routers.bookings.parse_booking_phrase", return_value=no_match):
        response = client.post("/bookings/nl", headers=headers, json={"phrase": "anything"})

    assert response.status_code == 404


def test_nl_booking_requires_auth(client):
    response = client.post("/bookings/nl", json={"phrase": "anything"})
    assert response.status_code == 401


def test_nl_booking_multiday_success(client, room):
    """A 7-day window always contains exactly 5 weekdays + 2 weekend days,
    regardless of which real day 'today' is -- avoids hardcoding a calendar date."""
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    start_day = future_date(7)
    end_day = future_date(13)

    fake_result = {
        "room_query": "Test Room", "date": start_day, "end_date": end_day,
        "start_time": "10:00", "duration_minutes": 60, "title": "Daily sync",
    }
    with patch("app.routers.bookings.parse_booking_phrase", return_value=fake_result):
        response = client.post("/bookings/nl", headers=headers, json={"phrase": "anything"})

    assert response.status_code == 201
    body = response.json()
    assert len(body["created"]) == 5
    assert len(body["skipped_weekends"]) == 2
    assert body["failed"] == []
    for booking in body["created"]:
        assert booking["room_id"] == room
        assert booking["title"] == "Daily sync"


def test_nl_booking_multiday_partial_conflict(client, room):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    start_day = future_date(7)
    end_day = future_date(13)

    d = datetime.fromisoformat(start_day).date()
    end_d = datetime.fromisoformat(end_day).date()
    conflict_day = next(day for day in (d + timedelta(n) for n in range((end_d - d).days + 1)) if day.weekday() < 5)

    client.post("/bookings", headers=headers, json={
        "room_id": room, "title": "Existing",
        "start_time": f"{conflict_day.isoformat()}T10:00:00", "end_time": f"{conflict_day.isoformat()}T11:00:00",
    })

    fake_result = {
        "room_query": "Test Room", "date": start_day, "end_date": end_day,
        "start_time": "10:00", "duration_minutes": 60, "title": "Daily sync",
    }
    with patch("app.routers.bookings.parse_booking_phrase", return_value=fake_result):
        response = client.post("/bookings/nl", headers=headers, json={"phrase": "anything"})

    assert response.status_code == 201
    body = response.json()
    assert len(body["created"]) == 4
    assert len(body["failed"]) == 1
    assert conflict_day.isoformat() in body["failed"][0]
