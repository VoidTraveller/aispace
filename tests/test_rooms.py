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
