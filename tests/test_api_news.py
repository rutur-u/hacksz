"""Campus news: public reading, staff publishing."""

from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models import User

NEWS = {
    "title": "Robotics club opens registration",
    "body": "Sign up at the student office before the end of the month.",
}


def test_staff_publish_news_and_everyone_reads_it(
    client: TestClient,
    register: Callable[..., dict[str, object]],
    login: Callable[[str, str], None],
    admin_user: User,
) -> None:
    login(admin_user.email, "staffpass123")
    created = client.post("/api/news", json=NEWS)
    assert created.status_code == 201, created.text
    news_id = created.json()["id"]
    assert created.json()["author_id"] == admin_user.id
    assert created.json()["published_at"] is not None

    # Reading is public; no cookie needed.
    client.cookies.clear()
    listing = client.get("/api/news").json()
    assert listing["total"] == 1
    assert listing["items"][0]["title"] == NEWS["title"]
    assert client.get(f"/api/news/{news_id}").status_code == 200
    assert client.get("/api/news/999").status_code == 404

    register(email="anna@uni.edu")
    login("anna@uni.edu", "secret123")
    assert client.get("/api/news").json()["total"] == 1


def test_students_cannot_publish_or_edit_news(
    client: TestClient,
    register: Callable[..., dict[str, object]],
    login: Callable[[str, str], None],
    admin_user: User,
) -> None:
    assert client.post("/api/news", json=NEWS).status_code == 401

    login(admin_user.email, "staffpass123")
    news_id = client.post("/api/news", json=NEWS).json()["id"]

    register(email="anna@uni.edu")
    login("anna@uni.edu", "secret123")
    assert client.post("/api/news", json=NEWS).status_code == 403
    assert client.patch(f"/api/news/{news_id}", json={"title": "Hijacked"}).status_code == 403
    assert client.delete(f"/api/news/{news_id}").status_code == 403


def test_staff_edit_and_delete_news(
    client: TestClient,
    login: Callable[[str, str], None],
    superadmin: User,
    admin_user: User,
) -> None:
    login(admin_user.email, "staffpass123")
    news_id = client.post("/api/news", json=NEWS).json()["id"]

    login(superadmin.email, "rootpass123")
    edited = client.patch(f"/api/news/{news_id}", json={"title": "Registration is open"})
    assert edited.status_code == 200
    assert edited.json()["title"] == "Registration is open"
    assert edited.json()["body"] == NEWS["body"]

    assert client.delete(f"/api/news/{news_id}").status_code == 204
    assert client.get("/api/news").json()["total"] == 0
    assert client.patch(f"/api/news/{news_id}", json={"title": "Gone"}).status_code == 404


def test_news_can_be_searched_by_keyword(
    client: TestClient,
    login: Callable[[str, str], None],
    admin_user: User,
) -> None:
    login(admin_user.email, "staffpass123")
    client.post("/api/news", json=NEWS)
    client.post(
        "/api/news",
        json={"title": "Library hours change", "body": "The library closes at eight now."},
    )

    found = client.get("/api/news", params={"q": "library"}).json()
    assert found["total"] == 1
    assert found["items"][0]["title"] == "Library hours change"
