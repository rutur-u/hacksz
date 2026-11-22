"""The admin-approval flow: student applies, main admin approves or rejects."""

from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models import User

APPLICATION = {
    "requested_position": "Student affairs admin",
    "department": "Student life",
    "motivation": "I want to help students find the right extra classes.",
}


def test_approval_promotes_student_and_creates_profile(
    client: TestClient,
    register: Callable[..., dict[str, object]],
    login: Callable[[str, str], None],
    superadmin: User,
) -> None:
    register(email="anna@uni.edu", password="secret123", student_number="202600123")
    login("anna@uni.edu", "secret123")

    created = client.post("/api/admin-applications", json=APPLICATION)
    assert created.status_code == 201
    application_id = created.json()["id"]
    assert created.json()["status"] == "pending"

    # A student cannot read the staff queue.
    assert client.get("/api/admin-applications").status_code == 403

    login(superadmin.email, "rootpass123")
    queue = client.get("/api/admin-applications").json()
    assert queue["total"] == 1
    assert queue["items"][0]["applicant"]["email"] == "anna@uni.edu"

    approved = client.post(
        f"/api/admin-applications/{application_id}/approve",
        json={"note": "Welcome aboard"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["reviewed_by_id"] == superadmin.id

    # The student is now an admin with a profile.
    login("anna@uni.edu", "secret123")
    me = client.get("/api/auth/me").json()
    assert me["user"]["role"] == "admin"
    assert me["admin_profile"]["position"] == "Student affairs admin"
    assert me["admin_profile"]["department"] == "Student life"
    assert me["admin_profile"]["approved_by_id"] == superadmin.id
    assert me["admin_profile"]["note"] == "Welcome aboard"

    # She left the student directory and joined the admin directory.
    login(superadmin.email, "rootpass123")
    assert client.get("/api/students").json()["total"] == 0
    admins = client.get("/api/admins").json()
    assert {item["email"] for item in admins["items"]} == {"root@uni.edu", "anna@uni.edu"}

    # Deciding twice is a conflict.
    assert (
        client.post(f"/api/admin-applications/{application_id}/approve").status_code == 409
    )


def test_only_one_pending_application_per_student(
    client: TestClient,
    register: Callable[..., dict[str, object]],
    login: Callable[[str, str], None],
) -> None:
    register(email="anna@uni.edu")
    login("anna@uni.edu", "secret123")

    assert client.post("/api/admin-applications", json=APPLICATION).status_code == 201
    assert client.post("/api/admin-applications", json=APPLICATION).status_code == 409


def test_rejection_keeps_student_and_allows_resubmission(
    client: TestClient,
    register: Callable[..., dict[str, object]],
    login: Callable[[str, str], None],
    superadmin: User,
) -> None:
    register(email="bob@uni.edu", password="secret123")
    login("bob@uni.edu", "secret123")
    application_id = client.post("/api/admin-applications", json=APPLICATION).json()["id"]

    login(superadmin.email, "rootpass123")
    rejected = client.post(
        f"/api/admin-applications/{application_id}/reject",
        json={"note": "Please apply next term"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["decision_note"] == "Please apply next term"

    login("bob@uni.edu", "secret123")
    me = client.get("/api/auth/me").json()
    assert me["user"]["role"] == "student"
    assert me["admin_profile"] is None
    assert client.get("/api/admin-applications/me").json()["total"] == 1

    # A rejected student may try again.
    assert client.post("/api/admin-applications", json=APPLICATION).status_code == 201


def test_regular_admin_cannot_decide_applications(
    client: TestClient,
    register: Callable[..., dict[str, object]],
    login: Callable[[str, str], None],
    admin_user: User,
) -> None:
    register(email="anna@uni.edu")
    login("anna@uni.edu", "secret123")
    application_id = client.post("/api/admin-applications", json=APPLICATION).json()["id"]

    login(admin_user.email, "staffpass123")
    response = client.post(f"/api/admin-applications/{application_id}/approve")
    assert response.status_code == 403
