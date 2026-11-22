"""Application entry point: templates, static files and page routes.

Run locally with::

    uvicorn app.main:app --reload
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import content, i18n
from app.api import api_router

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals.update(
    site_name=content.SITE_NAME,
    nav=content.NAV,
    current_year=datetime.now(timezone.utc).year,
)

app = FastAPI(title=content.SITE_NAME, version="0.1.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(api_router)


@app.middleware("http")
async def localize(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Select the page language and persist an explicit switch in a cookie."""
    requested = request.query_params.get("lang")
    request.state.locale = i18n.resolve_locale(
        requested=requested,
        stored=request.cookies.get(i18n.LANGUAGE_COOKIE),
        accept_language=request.headers.get("accept-language"),
    )
    response = await call_next(request)
    if i18n.is_supported(requested):
        response.set_cookie(
            i18n.LANGUAGE_COOKIE,
            request.state.locale,
            max_age=i18n.LANGUAGE_COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
        )
    return response


def render(request: Request, template_name: str, active: str, **context: object) -> HTMLResponse:
    """Render a template with the navigation state every page needs."""
    locale = request.state.locale
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context={
            "active": active,
            "locale": locale,
            "languages": i18n.LANGUAGES,
            "site_name": i18n.translate(locale, "site.name"),
            "t": lambda key, **values: i18n.translate(locale, key, **values),
            **context,
        },
    )


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return render(
        request,
        "index.html",
        active="home",
        news=content.NEWS,
        quick_links=content.QUICK_LINKS,
    )


@app.get("/register", response_class=HTMLResponse)
def register(request: Request) -> HTMLResponse:
    return render(request, "auth.html", active="register")


@app.get("/classes", response_class=HTMLResponse)
def search_classes(request: Request) -> HTMLResponse:
    return render(request, "classes.html", active="search")


@app.get("/classes/{class_id}", response_class=HTMLResponse)
def class_detail(request: Request, class_id: int) -> HTMLResponse:
    return render(request, "class_detail.html", active="search", class_id=class_id)


@app.get("/my-classes", response_class=HTMLResponse)
def my_classes(request: Request) -> HTMLResponse:
    return render(request, "my_classes.html", active="my_classes")


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request) -> HTMLResponse:
    return render(request, "admin.html", active="admin")


def _stub(request: Request, key: str) -> HTMLResponse:
    page = content.STUB_PAGES[key]
    return render(request, "stub.html", active=page["nav"], page=page)
