# Campus Extra Classes

A portal for tracking extracurricular classes at the university. Students browse the
catalogue, join classes and see their own weekly schedule. Staff publish classes and
manage capacity and rosters.

> **Status: skeleton.** The main page and the navigation shell are finished. Registration,
> search, "my classes" and administration are placeholder pages that the team is building.

## Stack

| Layer    | Choice                                                        |
| -------- | ------------------------------------------------------------- |
| Runtime  | Python 3.11+ (3.13 recommended)                                |
| Backend  | FastAPI + Uvicorn                                              |
| Views    | Jinja2 server-rendered templates                               |
| Styling  | Plain CSS with design tokens, no build step or CDN             |
| Storage  | none yet — SQLite is planned                                   |
| CI       | GitHub Actions: installs dependencies and runs `pytest`        |

## Quick start

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. Run the tests with `pytest`.

## Project layout

```
app/
  main.py              FastAPI app, routes, template setup
  content.py           temporary hard-coded content (news, nav, placeholder copy)
  templates/
    base.html          shared header, navigation, footer
    index.html         main page: hero, quick links, news
    stub.html          template used by every placeholder page
    _icons.html        inline SVG icon macro
  static/css/style.css design tokens and all page styles
tests/test_pages.py    smoke tests for every route
.github/workflows/ci.yml
```

## Pages

| Route         | Template      | Purpose                                        | Status      |
| ------------- | ------------- | ---------------------------------------------- | ----------- |
| `/`           | `index.html`  | Main page with news and quick links             | done        |
| `/register`   | `stub.html`   | Student sign-up, sign-in, password reset        | placeholder |
| `/classes`    | `stub.html`   | Search and filter the class catalogue           | placeholder |
| `/my-classes` | `stub.html`   | Personal weekly schedule and enrolment          | placeholder |
| `/admin`      | `stub.html`   | Staff CRUD for classes, capacity and rosters    | placeholder |

News items, navigation and placeholder copy live in [`app/content.py`](app/content.py).
Nothing there is connected to a database yet — that is intentional.

## Adding a page

1. Add the copy to `app/content.py` (or pass data from the route).
2. Add a route in `app/main.py` and a template in `app/templates/`.
3. Add the route to the smoke test in `tests/test_pages.py`.
4. Reuse existing classes (`.card`, `.btn`, `.pill`, `.section`); add new CSS only if needed.

## Team workflow

- **Issues first.** Every task has a GitHub issue with a label: `frontend`, `backend`,
  `data`, `docs` or `good first issue`. Comment on the issue before you start.
- **Branches.** `feat/<short-name>`, `fix/<short-name>`, `docs/<short-name>` from `main`.
- **Pull requests.** Small, one feature each. Link the issue (`Closes #12`), add a screenshot
  for UI changes, and keep CI green. One teammate review before merge.
- **Commits.** [Conventional Commits](https://www.conventionalcommits.org/):
  `feat: add class search results`, `fix: correct room label`, `docs: update setup steps`.
- **Never push to `main` directly.**

## Roadmap

- [ ] Data model for classes, sessions, students and enrolments (SQLite + SQLAlchemy)
- [ ] Registration and authentication
- [ ] Catalogue search with filters
- [ ] Personal schedule and enrolment actions
- [ ] Admin CRUD, CSV export
- [ ] Seed data and a demo account for reviews
