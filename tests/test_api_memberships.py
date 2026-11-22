"""Club roles: visitors self-join, staff promote members, members see extra content."""

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

OPEN_MEETING = {
    "weekday": 2,
    "start_time": "16:00:00",
    "end_time": "17:30:00",
    "room": "Lab 3",
    "audience": "everyone",
}

MEMBERS_MEETING = {
    "weekday": 4,
    "start_time": "18:00:00",
    "end_time": "19:00:00",
    "room": "Workshop",
    "audience": "members",
}

NEWS = {
    "title": "Robotics club news",
    "body": "Something happened at the club this week.",
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


def _join(client: TestClient, class_id: object) -> dict[str, object]:
    response = client.post(f"/api/classes/{class_id}/membership")
    assert response.status_code == 201, response.text
    return response.json()


def test_visitors_self_join_with_one_role_per_club(
    client: TestClient,
    register: Callable[..., dict[str, object]],
    login: Callable[[str, str], None],
    superadmin: User,
) -> None:
    course = _create_class(client, superadmin, login)

    client.cookies.clear()
    assert client.post(f"/api/classes/{course['id']}/membership").status_code == 401

    register(email="anna@uni.edu", password="secret123", full_name="Anna Lee")
    login("anna@uni.edu", "secret123")
    joined = _join(client, course["id"])
    assert joined["role"] == "visitor"
    assert joined["user"]["email"] == "anna@uni.edu"

    # One role per person per club: a second join is rejected.
    assert client.post(f"/api/classes/{course['id']}/membership").status_code == 409

    # Draft clubs cannot be joined at all.
    draft = _create_class(client, superadmin, login, code="drafty", status="draft")
    login("anna@uni.edu", "secret123")
    assert client.post(f"/api/classes/{draft['id']}/membership").status_code == 409
    assert client.post("/api/classes/999/membership").status_code == 404


def test_staff_manage_memberships(
    client: TestClient,
    register: Callable[..., dict[str, object]],
    login: Callable[[str, str], None],
    superadmin: User,
    admin_user: User,
) -> None:
    course = _create_class(client, superadmin, login)
    url = f"/api/classes/{course['id']}/memberships"
    student = register(email="bob@uni.edu", password="secret123", full_name="Bob Stone")

    login("bob@uni.edu", "secret123")
    _join(client, course["id"])
    assert client.get(url).status_code == 403
    assert (
        client.patch(f"{url}/{student['id']}", json={"role": "member"}).status_code == 403
    )

    login(admin_user.email, "staffpass123")
    listing = client.get(url).json()
    assert listing["total"] == 1
    assert listing["items"][0]["role"] == "visitor"
    assert listing["items"][0]["user"]["email"] == "bob@uni.edu"

    promoted = client.patch(f"{url}/{student['id']}", json={"role": "member"})
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "member"
    assert client.get(url, params={"role": "member"}).json()["total"] == 1
    assert client.get(url, params={"role": "visitor"}).json()["total"] == 0

    assert (
        client.patch(f"{url}/999", json={"role": "member"}).status_code == 404
    )
    assert client.delete(f"{url}/{student['id']}").status_code == 204
    assert client.get(url).json()["total"] == 0
    assert client.delete(f"{url}/{student['id']}").status_code == 404


def test_members_only_meetings_are_hidden_from_visitors(
    client: TestClient,
    register: Callable[..., dict[str, object]],
    login: Callable[[str, str], None],
    superadmin: User,
    admin_user: User,
) -> None:
    course = _create_class(client, superadmin, login)
    meetings_url = f"/api/classes/{course['id']}/meetings"

    login(admin_user.email, "staffpass123")
    assert client.post(meetings_url, json=OPEN_MEETING).status_code == 201
    assert client.post(meetings_url, json=MEMBERS_MEETING).status_code == 201

    # Staff see both slots; outsiders and visitors see only the open one.
    detail_url = f"/api/classes/{course['id']}"
    assert len(client.get(detail_url).json()["meetings"]) == 2

    student = register(email="anna@uni.edu", password="secret123", full_name="Anna Lee")
    login("anna@uni.edu", "secret123")
    _join(client, course["id"])
    visitor_detail = client.get(detail_url).json()
    assert [item["audience"] for item in visitor_detail["meetings"]] == ["everyone"]

    # The visitor is promoted to member and the extra slot appears.
    login(admin_user.email, "staffpass123")
    client.patch(
        f"/api/classes/{course['id']}/memberships/{student['id']}",
        json={"role": "member"},
    )
    login("anna@uni.edu", "secret123")
    member_detail = client.get(detail_url).json()
    assert {item["audience"] for item in member_detail["meetings"]} == {
        "everyone",
        "members",
    }

    # A member of another club still does not see this club's private slot.
    register(email="cara@uni.edu", password="secret123", full_name="Cara Diaz")
    login("cara@uni.edu", "secret123")
    other_detail = client.get(detail_url).json()
    assert [item["audience"] for item in other_detail["meetings"]] == ["everyone"]


def test_members_only_news_is_scoped_to_club_members(
    client: TestClient,
    register: Callable[..., dict[str, object]],
    login: Callable[[str, str], None],
    superadmin: User,
    admin_user: User,
) -> None:
    course = _create_class(client, superadmin, login)
    other_course = _create_class(
        client, superadmin, login, code="chess", title="Chess Club"
    )

    login(admin_user.email, "staffpass123")
    public_post = client.post(
        "/api/news",
        json={"title": "Campus open day", "body": "Everyone is welcome on Saturday."},
    )
    assert public_post.status_code == 201
    members_post = client.post(
        "/api/news",
        json={**NEWS, "class_id": course["id"], "audience": "members"},
    )
    assert members_post.status_code == 201, members_post.text
    members_id = members_post.json()["id"]
    assert members_post.json()["class_id"] == course["id"]

    # Members-only news must belong to a club.
    assert (
        client.post(
            "/api/news", json={**NEWS, "audience": "members"}
        ).status_code
        == 422
    )
    # And a public post cannot be moved to members-only without a club.
    assert (
        client.patch(
            f"/api/news/{public_post.json()['id']}", json={"audience": "members"}
        ).status_code
        == 422
    )

    # Anonymous readers only see public posts.
    client.cookies.clear()
    anonymous = client.get("/api/news").json()
    assert {item["id"] for item in anonymous["items"]} == {public_post.json()["id"]}
    assert client.get(f"/api/news/{members_id}").status_code == 404

    # A visitor of the club still does not see members news.
    student = register(email="anna@uni.edu", password="secret123", full_name="Anna Lee")
    login("anna@uni.edu", "secret123")
    _join(client, course["id"])
    assert client.get(f"/api/news/{members_id}").status_code == 404
    assert client.get("/api/news").json()["total"] == 1

    # Once promoted to member, the club post is visible.
    login(admin_user.email, "staffpass123")
    client.patch(
        f"/api/classes/{course['id']}/memberships/{student['id']}",
        json={"role": "member"},
    )
    login("anna@uni.edu", "secret123")
    assert client.get(f"/api/news/{members_id}").status_code == 200
    assert client.get("/api/news").json()["total"] == 2

    # Being a member of a different club is not enough.
    cara = register(email="cara@uni.edu", password="secret123", full_name="Cara Diaz")
    login("cara@uni.edu", "secret123")
    _join(client, other_course["id"])
    login(admin_user.email, "staffpass123")
    client.patch(
        f"/api/classes/{other_course['id']}/memberships/{cara['id']}",
        json={"role": "member"},
    )
    login("cara@uni.edu", "secret123")
    assert client.get(f"/api/news/{members_id}").status_code == 404
    assert client.get("/api/news").json()["total"] == 1
