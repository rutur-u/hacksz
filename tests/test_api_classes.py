"""Class catalogue and weekly meeting slots."""

from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models import User

CLASS = {
    "code": "robotics",
    "title": "Robotics Club",
    "description": "Build small robots in a team.",
    "category": "Engineering",
    "teacher_name": "Dr Novak",
    "capacity": 20,
    "status": "published",
}

MEETING = {
    "weekday": 2,
    "start_time": "16:00:00",
    "end_time": "17:30:00",
    "room": "Lab 3",
}


def _create_class(
    client: TestClient,
    superadmin: User,
    login: Callable[[str, str], None],
    **overrides: object,
) -> dict[str, object]:
    login(superadmin.email, "rootpass123")
    response = client.post("/api/classes", json={**CLASS, **overrides})
    assert response.status_code == 201, response.text
    return response.json()


def test_public_catalogue_hides_unpublished_classes(
    client: TestClient,
    register: Callable[..., dict[str, object]],
    login: Callable[[str, str], None],
    superadmin: User,
) -> None:
    draft = _create_class(client, superadmin, login, code="drafty", status="draft")
    published = _create_class(client, superadmin, login)

    client.cookies.clear()
    listing = client.get("/api/classes").json()
    assert listing["total"] == 1
    assert listing["items"][0]["code"] == "ROBOTICS"
    assert listing["items"][0]["meetings"] == []
    assert client.get(f"/api/classes/{draft['id']}").status_code == 404
    assert client.get(f"/api/classes/{published['id']}").status_code == 200

    # A student still only sees the published catalogue.
    register(email="anna@uni.edu")
    login("anna@uni.edu", "secret123")
    assert client.get("/api/classes").json()["total"] == 1
    assert client.get(f"/api/classes/{draft['id']}").status_code == 404

    # Staff see everything and can filter by status.
    login(superadmin.email, "rootpass123")
    assert client.get("/api/classes").json()["total"] == 2
    drafts = client.get("/api/classes", params={"status": "draft"}).json()
    assert drafts["total"] == 1
    assert drafts["items"][0]["id"] == draft["id"]
    assert client.get(f"/api/classes/{draft['id']}").status_code == 200


def test_only_main_admin_creates_edits_and_archives(
    client: TestClient,
    register: Callable[..., dict[str, object]],
    login: Callable[[str, str], None],
    superadmin: User,
    admin_user: User,
) -> None:
    assert client.post("/api/classes", json=CLASS).status_code == 401

    register(email="anna@uni.edu")
    login("anna@uni.edu", "secret123")
    assert client.post("/api/classes", json=CLASS).status_code == 403

    login(admin_user.email, "staffpass123")
    assert client.post("/api/classes", json=CLASS).status_code == 403

    course = _create_class(client, superadmin, login)
    # Codes are unique regardless of case and stored upper-case.
    assert course["code"] == "ROBOTICS"
    assert (
        client.post("/api/classes", json={**CLASS, "code": "Robotics"}).status_code
        == 409
    )

    patched = client.patch(
        f"/api/classes/{course['id']}",
        json={"title": "Robotics Lab", "capacity": 25},
    )
    assert patched.status_code == 200
    assert patched.json()["title"] == "Robotics Lab"
    assert patched.json()["capacity"] == 25
    assert client.patch("/api/classes/999", json={"title": "Ghost"}).status_code == 404

    archived = client.post(f"/api/classes/{course['id']}/archive")
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    client.cookies.clear()
    assert client.get("/api/classes").json()["total"] == 0
    assert client.get(f"/api/classes/{course['id']}").status_code == 404


def test_search_shortlist_filters_by_keyword_and_category(
    client: TestClient,
    login: Callable[[str, str], None],
    superadmin: User,
) -> None:
    _create_class(client, superadmin, login)
    _create_class(
        client,
        superadmin,
        login,
        code="chess",
        title="Chess Club",
        description="Weekly games evening for all levels.",
        category="Games",
        teacher_name="Ms Petrov",
    )

    by_title = client.get("/api/classes", params={"q": "robot"}).json()
    assert [item["code"] for item in by_title["items"]] == ["ROBOTICS"]
    by_teacher = client.get("/api/classes", params={"q": "petrov"}).json()
    assert [item["code"] for item in by_teacher["items"]] == ["CHESS"]
    by_category = client.get("/api/classes", params={"category": "Games"}).json()
    assert [item["code"] for item in by_category["items"]] == ["CHESS"]


def test_staff_manage_weekly_slots(
    client: TestClient,
    register: Callable[..., dict[str, object]],
    login: Callable[[str, str], None],
    superadmin: User,
    admin_user: User,
) -> None:
    course = _create_class(client, superadmin, login)
    url = f"/api/classes/{course['id']}/meetings"

    register(email="anna@uni.edu")
    login("anna@uni.edu", "secret123")
    assert client.post(url, json=MEETING).status_code == 403

    login(admin_user.email, "staffpass123")
    created = client.post(url, json=MEETING)
    assert created.status_code == 201, created.text
    meeting_id = created.json()["id"]
    assert created.json()["room"] == "Lab 3"

    # The same class cannot book two slots at the same weekday and time.
    assert client.post(url, json=MEETING).status_code == 409

    # The end of a slot must be after its start.
    bad = {**MEETING, "weekday": 3, "start_time": "18:00:00", "end_time": "17:00:00"}
    assert client.post(url, json=bad).status_code == 422

    moved = client.patch(f"{url}/{meeting_id}", json={"room": "Lab 5", "weekday": 4})
    assert moved.status_code == 200
    assert moved.json()["room"] == "Lab 5"
    assert moved.json()["weekday"] == 4

    detail = client.get(f"/api/classes/{course['id']}").json()
    assert detail["meetings"][0]["room"] == "Lab 5"

    assert client.delete(f"{url}/{meeting_id}").status_code == 204
    assert client.get(f"/api/classes/{course['id']}").json()["meetings"] == []
    assert client.delete(f"{url}/{meeting_id}").status_code == 404
