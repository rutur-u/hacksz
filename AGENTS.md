# AGENTS.md

Guidance for AI coding assistants working in this repository. Read it before changing code.

## What this is

A FastAPI + Jinja2 portal for extracurricular classes at a university. The main page, the
navigation shell, the accounts API, the class catalogue with club roles (visitor/member) and
weekly meeting slots, plus campus and club news exist. Public feature pages are deliberate
placeholders; the search ranking and enrolments are another teammate's work.

## Commands

| Task             | Command                                                          |
| ---------------- | ---------------------------------------------------------------- |
| Install          | `pip install -r requirements-dev.txt`                             |
| Migrate          | `alembic upgrade head`                                            |
| Run              | `uvicorn app.main:app --reload`                                   |
| Test             | `pytest`                                                          |
| New migration    | `alembic revision --autogenerate -m "what changed"`               |
| First main admin | `python -m app.cli create-superadmin --email you@uni.edu --name "Your Name"` |

## Where things live

- `app/main.py` — page routes and app wiring. One function per public page.
- `app/api/` — JSON endpoints under `/api`; `deps.py` holds auth and role checks.
- `app/models.py` — every SQLAlchemy table, including classes, weekly slots and news. The
  search teammate adds enrolment tables here too.
- `app/services.py` — business rules (registration, login, approvals, classes, meetings,
  news) that must hold for every caller. Routers stay thin.
- `app/schemas.py` — Pydantic request/response models.
- `app/db.py`, `app/config.py`, `app/security.py` — engine, settings, hashing and tokens.
- `alembic/versions/` — schema history. Never change a migrated table without a new revision.
- `Dockerfile` and `render.yaml` — production image and Render Blueprint. Deployment is
  additive; do not special-case container paths in app code.
- `tests/` — `test_pages.py` for HTML, `test_api_*.py` for the API (in-memory SQLite).

## Conventions

- Server-rendered Jinja2 and plain CSS. Do **not** introduce React/Vue/Tailwind, a bundler,
  a CDN stylesheet or a JS framework without team agreement in an issue.
- Do not touch templates or CSS when the task is data-only; the visual layer has its owner.
- New data features are JSON endpoints under `/api`, never HTML pages in this module.
- Reuse `.card`, `.btn`, `.pill`, `.section`, `.stub` and the `icon()` macro before writing
  new CSS or new markup patterns.
- Every user-facing page needs: a route in `app/main.py`, a template, a nav entry when it
  belongs in the header, and a case in `tests/test_pages.py`.
- Every schema change needs an Alembic revision committed with the model change.
- Python: type hints on public functions, double quotes, 4-space indent, lines under 100 chars.
- Templates: 2-space indent, one block per page, semantic HTML, `aria-current` for the active
  nav item.
- Accessibility: every interactive element is a real link or button, icons are decorative
  (`aria-hidden="true"`), colour is never the only signal.
- Security: lowercase-normalise emails, never store raw passwords or raw session tokens,
  never return `password_hash`, always check roles server-side.
- Public endpoints that also serve staff (catalogue, class detail, news) use
  `get_optional_user` and hide unpublished rows and members-only content from everyone else.
- Club roles: visitors self-join a published class; only staff promote a visitor to member.
  One membership per person per club keeps the two roles mutually exclusive.
- No secrets, no `.env` files, no `.venv`, `app.db` or generated files in commits.

## Definition of done

- `pytest` passes and the new behaviour has a test.
- `alembic upgrade head` works from an empty database.
- Page renders correctly at 1440 px and 390 px widths (UI tasks only).
- Placeholder pages still say "Planned" and link back to the main page.
- Commit messages follow Conventional Commits; the PR links its issue.

## Do not

- Do not add enrolment or search-ranking tables without coordinating with their owner; the
  class, meeting and news tables are already ours.
- Do not edit `app.db` by hand or squash migrations that teammates already pulled.
- Do not redesign the visual system or rename existing CSS classes as a side effect.
- Do not delete the placeholder routes — features replace them in place.
- Do not commit directly to `main`.
