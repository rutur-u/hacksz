"""Tests for JSON localization and language selection."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.i18n import LOCALE_DIR, SUPPORTED_LOCALES


def test_english_is_the_fallback_language(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert '<html lang="en">' in response.text
    assert "Every extra class on campus" in response.text
    assert response.cookies.get("lang") is None


def test_russian_selection_persists_across_routes(client: TestClient) -> None:
    response = client.get("/?lang=ru")
    assert response.status_code == 200
    assert '<html lang="ru">' in response.text
    assert "Главная" in response.text
    assert response.cookies.get("lang") == "ru"

    classes = client.get("/classes")
    assert '<html lang="ru">' in classes.text
    assert "Мои занятия" in classes.text

    stub = client.get("/my-classes")
    assert '<html lang="ru">' in stub.text
    assert "Главная" in stub.text


def test_simplified_chinese_selection_persists_across_routes(client: TestClient) -> None:
    response = client.get("/?lang=zh")
    assert response.status_code == 200
    assert '<html lang="zh">' in response.text
    assert "课程管理" in response.text
    assert response.cookies.get("lang") == "zh"

    register = client.get("/register")
    assert '<html lang="zh">' in register.text
    assert "注册" in register.text


def test_browser_language_is_used_without_a_saved_choice(client: TestClient) -> None:
    russian = client.get("/", headers={"Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"})
    assert '<html lang="ru">' in russian.text

    client.cookies.clear()
    chinese = client.get("/", headers={"Accept-Language": "zh-CN,zh;q=0.9"})
    assert '<html lang="zh">' in chinese.text

    client.cookies.clear()
    unsupported = client.get("/", headers={"Accept-Language": "fr-FR,fr;q=0.9"})
    assert '<html lang="en">' in unsupported.text


def test_invalid_selection_does_not_replace_the_saved_language(client: TestClient) -> None:
    client.get("/?lang=ru")
    response = client.get("/?lang=invalid")
    assert '<html lang="ru">' in response.text


def test_all_page_routes_render_in_every_language(client: TestClient) -> None:
    for locale in SUPPORTED_LOCALES:
        for path in ("/", "/classes", "/register", "/my-classes", "/admin"):
            response = client.get(f"{path}?lang={locale}")
            assert response.status_code == 200, (path, locale)
            assert f'<html lang="{locale}">' in response.text, (path, locale)
            assert 'class="language-switcher"' in response.text, (path, locale)


def test_locale_dictionaries_have_matching_complete_keys() -> None:
    dictionaries = {}
    for locale in SUPPORTED_LOCALES:
        with (LOCALE_DIR / f"{locale}.json").open(encoding="utf-8") as locale_file:
            dictionaries[locale] = json.load(locale_file)
        assert all(dictionaries[locale].values()), locale

    expected = set(dictionaries["en"])
    assert set(dictionaries["ru"]) == expected
    assert set(dictionaries["zh"]) == expected


def test_locale_directory_contains_only_supported_dictionaries() -> None:
    files = {path.stem for path in Path(LOCALE_DIR).glob("*.json")}
    assert files == set(SUPPORTED_LOCALES)
