import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.database import engine


@pytest.fixture(autouse=True)
def clean_db():
    """Truncate all tables before every test, so each test starts from a known empty state."""
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE bookings, users, rooms RESTART IDENTITY CASCADE"))
        conn.commit()
    yield

@pytest.fixture
def client():
    return TestClient(app)