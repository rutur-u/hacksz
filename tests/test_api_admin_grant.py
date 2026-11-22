"""The main admin grants the admin role directly, without an application."""

from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models import User


def test_main_admin_grants_admin_role(
    client: TestClient,
    register: Callable[..., dict[str, object]],
    login: Callable[[str, str], None],
    superadmin: User,
) -> None:
    student = register(email="bob@uni.edu", password="secret123", full_name="Bob Stone")

    login(superadmin.email, "rootpass123")
    granted = client.post(
        "/api/admins/grant",
        json={"user_id": student["id"], "position": "Events admin", "department": "Student life"},
    )
    assert granted.status_code == 201, granted.text
    assert granted.json()["role"] == "admin"
    assert granted.json()["profile"]["position"] == "Events admin"
    assert granted.json()["profile"]["approved_by_id"] == superadmin.id

    # The person now has an admin profile and can post news.
    login("bob@uni.edu", "secret123")
    me = client.get("/api/auth/me").json()
    assert me["user"]["role"] == "admin"
    assert me["admin_profile"]["position"] == "Events admin"
    assert client.post(
        "/api/news",
        json={"title": "First post", "body": "Written by the new events admin."},
    ).status_code == 201

    # Granting twice, or to a superadmin, is a conflict.
    login(superadmin.email, "rootpass123")
    assert client.post("/api/admins/grant", json={"user_id": student["id"]}).status_code == 409
    assert client.post("/api/admins/grant", json={"user_id": superadmin.id}).status_code == 409
    assert client.post("/api/admins/grant", json={"user_id": 999}).status_code == 404


def test_only_main_admin_can_grant(
    client: TestClient,
    register: Callable[..., dict[str, object]],
    login: Callable[[str, str], None],
    admin_user: User,
) -> None:
    student = register(email="bob@uni.edu")

    assert client.post("/api/admins/grant", json={"user_id": student["id"]}).status_code == 401

    login("bob@uni.edu", "secret123")
    assert client.post("/api/admins/grant", json={"user_id": student["id"]}).status_code == 403

    login(admin_user.email, "staffpass123")
    assert client.post("/api/admins/grant", json={"user_id": student["id"]}).status_code == 403
