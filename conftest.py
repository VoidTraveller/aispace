import os
import subprocess
from datetime import date, timedelta

import psycopg2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import get_db
from app.main import app

# separate test database, never the real one -- same DATABASE_URL, different db name
TEST_DATABASE_URL = settings.database_url.rsplit("/", 1)[0] + "/aispace_test"

test_engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def _ensure_test_database_exists():
    """Creates aispace_test if missing (autocommit: CREATE DATABASE can't run in a transaction)."""
    conn = psycopg2.connect(settings.database_url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = 'aispace_test'")
            if cur.fetchone() is None:
                cur.execute("CREATE DATABASE aispace_test")
    finally:
        conn.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Applies the real Alembic migrations to aispace_test, so its schema matches production exactly."""
    _ensure_test_database_exists()
    subprocess.run(
        ["python", "-m", "alembic", "upgrade", "head"],
        env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL},
        check=True,
    )


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def clean_db(setup_test_database):
    """Truncate the TEST database before every test -- the real app database is never touched."""
    with test_engine.connect() as conn:
        conn.execute(text("TRUNCATE bookings, users, rooms RESTART IDENTITY CASCADE"))
        conn.commit()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def future_date(days_ahead=7):
    """Relative date, not hardcoded -- a fixed date eventually becomes the past."""
    return (date.today() + timedelta(days=days_ahead)).isoformat()


def past_date(days_ago=1):
    return (date.today() - timedelta(days=days_ago)).isoformat()


def register_and_login(client, email="tester@test.com"):
    """Shared helper (not a fixture, since email varies per test): register + login, return a bearer token."""
    client.post("/auth/register", json={
        "email": email, "password": "testpass123", "first_name": "Test", "last_name": "User",
    })
    response = client.post("/auth/login", data={"username": email, "password": "testpass123"})
    return response.json()["access_token"]


def _create_room(is_active=True):
    from app.models import Room

    db = TestSessionLocal()
    try:
        room = Room(name="Test Room", capacity=4, description="test room", is_active=is_active)
        db.add(room)
        db.commit()
        db.refresh(room)
        return room.id
    finally:
        db.close()


@pytest.fixture
def room():
    """A fresh, active room created directly in the TEST DB -- tests never rely on app-seeded room IDs."""
    return _create_room(is_active=True)


@pytest.fixture
def inactive_room():
    return _create_room(is_active=False)
