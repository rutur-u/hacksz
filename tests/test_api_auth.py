"""Registration, login and access-control tests for the account API."""

from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models import User


def test_register_creates_student_with_profile(
    client: TestClient, register: Callable[..., dict[str, object]]
) -> None:
    body = register(
        email="  Anna.Lee@Uni.EDU ",
        full_name="Anna Lee",
        student_number="202600123",
        faculty="Engineering",
        study_year=2,
    )

    assert body["email"] == "anna.lee@uni.edu"
    assert body["role"] == "student"
    assert body["status"] == "active"
    assert "password" not in body
    assert "password_hash" not in body


def test_register_rejects_duplicate_email(
    client: TestClient, register: Callable[..., dict[str, object]]
) -> None:
    register(email="anna@uni.edu")

    response = client.post(
        "/api/auth/register",
        json={"email": "ANNA@uni.edu", "password": "secret123", "full_name": "Anna Again"},
    )

    assert response.status_code == 409


def test_register_enforces_password_length(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "short@uni.edu", "password": "short", "full_name": "Short Pass"},
    )
    assert response.status_code == 422


def test_login_me_logout_cycle(
    client: TestClient, register: Callable[..., dict[str, object]]
) -> None:
    register(email="anna@uni.edu", password="secret123", student_number="202600123")

    response = client.post(
        "/api/auth/login", json={"email": "anna@uni.edu", "password": "secret123"}
    )
    assert response.status_code == 200
    assert "httponly" in response.headers["set-cookie"].lower()

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    payload = me.json()
    assert payload["user"]["email"] == "anna@uni.edu"
    assert payload["student_profile"]["student_number"] == "202600123"
    assert payload["admin_profile"] is None

    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_login_rejects_wrong_password(
    client: TestClient, register: Callable[..., dict[str, object]]
) -> None:
    register(email="anna@uni.edu", password="secret123")

    response = client.post(
        "/api/auth/login", json={"email": "anna@uni.edu", "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_me_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/students").status_code == 401


def test_students_cannot_read_the_directory(
    client: TestClient,
    register: Callable[..., dict[str, object]],
    login: Callable[[str, str], None],
) -> None:
    register(email="anna@uni.edu")
    login("anna@uni.edu", "secret123")

    assert client.get("/api/students").status_code == 403
    assert client.get("/api/admins").status_code == 403


def test_staff_can_list_and_filter_students(
    client: TestClient,
    register: Callable[..., dict[str, object]],
    login: Callable[[str, str], None],
    admin_user: User,
) -> None:
    register(email="anna@uni.edu", full_name="Anna Lee", student_number="202600123")
    register(email="bob@uni.edu", full_name="Bob Stone", student_number="202600456")

    login("staff@uni.edu", "staffpass123")

    everything = client.get("/api/students").json()
    assert everything["total"] == 2

    filtered = client.get("/api/students", params={"q": "202600456"}).json()
    assert filtered["total"] == 1
    assert filtered["items"][0]["email"] == "bob@uni.edu"
    assert filtered["items"][0]["profile"]["student_number"] == "202600456"
