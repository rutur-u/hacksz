"""Shared test fixtures: an isolated in-memory database and an API client."""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Role, User, UserStatus
from app.security import hash_password


@pytest.fixture()
def session_factory() -> Iterator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield factory
    engine.dispose()


@pytest.fixture()
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def superadmin(session_factory: sessionmaker[Session]) -> User:
    with session_factory() as db:
        user = User(
            email="root@uni.edu",
            full_name="Main Admin",
            password_hash=hash_password("rootpass123"),
            role=Role.SUPERADMIN,
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture()
def admin_user(session_factory: sessionmaker[Session]) -> User:
    with session_factory() as db:
        user = User(
            email="staff@uni.edu",
            full_name="Staff Member",
            password_hash=hash_password("staffpass123"),
            role=Role.ADMIN,
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture()
def register(client: TestClient) -> Callable[..., dict[str, object]]:
    def _register(
        email: str = "anna@uni.edu",
        password: str = "secret123",
        full_name: str = "Anna Lee",
        **extra: object,
    ) -> dict[str, object]:
        response = client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "full_name": full_name, **extra},
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _register


@pytest.fixture()
def login(client: TestClient) -> Callable[[str, str], None]:
    def _login(email: str, password: str) -> None:
        response = client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 200, response.text

    return _login
