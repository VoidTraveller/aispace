def test_register_creates_user(client):
    response = client.post("/auth/register", json={
        "email": "alice@test.com",
        "password": "securepass123",
        "first_name": "Alice",
        "last_name": "Smith",
    })
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@test.com"
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_duplicate_email_rejected(client):
    payload = {"email": "bob@test.com", "password": "securepass123", "first_name": "Bob", "last_name": "Jones"}
    client.post("/auth/register", json=payload)
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 409


def test_login_wrong_password_rejected(client):
    client.post("/auth/register", json={
        "email": "carol@test.com", "password": "correctpass", "first_name": "Carol", "last_name": "Lee",
    })
    response = client.post("/auth/login", data={"username": "carol@test.com", "password": "wrongpass"})
    assert response.status_code == 401


def test_login_success_returns_token(client):
    client.post("/auth/register", json={
        "email": "dave@test.com", "password": "correctpass", "first_name": "Dave", "last_name": "Kim",
    })
    response = client.post("/auth/login", data={"username": "dave@test.com", "password": "correctpass"})
    assert response.status_code == 200
    assert "access_token" in response.json()