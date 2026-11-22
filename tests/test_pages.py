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
    for title in ("Register", "Find a class", "My classes", "Class administration"):
        assert f"<h3>{title}</h3>" in response.text, title


def test_working_feature_pages_render() -> None:
    expected = {
        "/register": ("Create an account", "js/auth.js"),
        "/classes": ("Find your next extra class", "js/classes.js"),
        "/my-classes": ("My classes", "js/my-classes.js"),
        "/admin": ("Class administration", "js/admin.js"),
    }
    for path, markers in expected.items():
        response = client.get(path)
        assert response.status_code == 200, path
        for marker in markers:
            assert marker in response.text, (path, marker)
        assert "Planned" not in response.text, path


def test_class_detail_page_renders() -> None:
    response = client.get("/classes/42")
    assert response.status_code == 200
    assert 'data-class-id="42"' in response.text
    assert "Back to all classes" in response.text
    assert "js/class-detail.js" in response.text


def test_staff_navigation_is_hidden_until_authorised() -> None:
    response = client.get("/")
    assert "data-staff-link hidden" in response.text
    assert "js/site.js" in response.text


def test_stylesheet_is_served() -> None:
    response = client.get("/static/css/style.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")


def test_university_icon_is_used_and_served() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.text.count("/static/images/smbu-favicon.ico") == 2

    icon = client.get("/static/images/smbu-favicon.ico")
    assert icon.status_code == 200
    assert icon.headers["content-type"] in ("image/x-icon", "image/vnd.microsoft.icon")
