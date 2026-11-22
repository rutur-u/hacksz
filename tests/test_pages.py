"""Smoke tests for the page shell.

Run with:  pytest
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_home_page_renders() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Every extra class on campus" in response.text
    assert "News &amp; updates" in response.text


def test_placeholder_pages_render() -> None:
    for path in ("/register", "/classes", "/my-classes", "/admin"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert "Planned" in response.text, path
        assert "Back to main page" in response.text, path


def test_stylesheet_is_served() -> None:
    response = client.get("/static/css/style.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
