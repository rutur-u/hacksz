"""Application entry point: templates, static files and page routes.

Run locally with::

    uvicorn app.main:app --reload
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import content

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals.update(
    site_name=content.SITE_NAME,
    nav=content.NAV,
    current_year=datetime.now(timezone.utc).year,
)

app = FastAPI(title=content.SITE_NAME, version="0.1.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def render(request: Request, template_name: str, active: str, **context: object) -> HTMLResponse:
    """Render a template with the navigation state every page needs."""
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context={"active": active, **context},
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


# --- Placeholder pages -------------------------------------------------------
# The shell is finished; each feature below is owned by a teammate.
@app.get("/register", response_class=HTMLResponse)
def register(request: Request) -> HTMLResponse:
    return _stub(request, "register")


@app.get("/classes", response_class=HTMLResponse)
def search_classes(request: Request) -> HTMLResponse:
    return _stub(request, "search")


@app.get("/my-classes", response_class=HTMLResponse)
def my_classes(request: Request) -> HTMLResponse:
    return _stub(request, "my_classes")


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request) -> HTMLResponse:
    return _stub(request, "admin")


def _stub(request: Request, key: str) -> HTMLResponse:
    page = content.STUB_PAGES[key]
    return render(request, "stub.html", active=page["nav"], page=page)
