import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["MOCK_AI_MODE"] = "true"
os.environ["ADMIN_EMAILS"] = '["test@example.com"]'

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base, get_db
from app.main import create_app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

app = create_app()


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def get_auth_headers(client: TestClient) -> dict[str, str]:
    signup_payload = {"email": "test@example.com", "password": "password123", "full_name": "Tester"}
    response = client.post("/auth/signup", json=signup_payload)
    if response.status_code == 201:
        token = response.json()["access_token"]
    else:
        login_response = client.post("/auth/login", json={"email": signup_payload["email"], "password": signup_payload["password"]})
        token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


import pytest


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
