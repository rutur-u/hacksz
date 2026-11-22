# smbuclubs

A portal for tracking extracurricular classes at the university. Students browse the
catalogue, join classes and see their own weekly schedule. Staff publish classes and
manage capacity and rosters.

> **Status: accounts + catalogue backend.** The main page, the navigation shell, the
> accounts/admin-approval API, the class catalogue with club roles (member/visitor) and
> weekly meeting slots, campus and club news, and direct admin grants are done. The public
> pages are still placeholders and the visual layer is owned by another teammate; the
> search ranking is the search teammate's work.

## Stack

| Layer    | Choice                                                       |
| -------- | ------------------------------------------------------------ |
| Runtime  | Python 3.11+ (3.13 recommended)                               |
| Backend  | FastAPI + Uvicorn                                             |
| Views    | Jinja2 server-rendered templates                              |
| Styling  | Plain CSS with design tokens, no build step or CDN            |
| Storage  | SQLite + SQLAlchemy 2.0, schema versioned with Alembic        |
| Auth     | Argon2 password hashes, opaque session token in an HttpOnly cookie |
| CI       | GitHub Actions: installs dependencies and runs `pytest`       |

## Quick start

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
alembic upgrade head
python -m app.cli create-superadmin --email root@uni.edu --name "Main Admin"
uvicorn app.main:app --reload
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
python -m app.cli create-superadmin --email root@uni.edu --name "Main Admin"
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000> for the site and <http://127.0.0.1:8000/docs> for the API
explorer. Run the tests with `pytest`.

Environment variables (all optional locally):

| Variable                | Default              | Purpose                                  |
| ----------------------- | -------------------- | ---------------------------------------- |
| `DATABASE_URL`          | `sqlite:///./app.db` | Database connection string               |
| `SESSION_COOKIE_SECURE` | `0`                  | Set to `1` behind HTTPS so the cookie is `Secure` |

## Deploy to Render

The repository ships a `Dockerfile` and a `render.yaml` blueprint. Deployment is additive:
it adds container files only and changes no templates, CSS, routes or API code, so future
frontend and search commits keep working and auto-deploy on every push to `main`.

1. Push to GitHub and open Render → **New → Blueprint**, pick this repository, apply.
2. Render builds the image, runs `alembic upgrade head` and starts uvicorn on `$PORT`.
3. SQLite lives at `/data/app.db` on a 1 GB persistent disk, so data survives restarts.
4. Create the first main admin once from the Render **Shell**:

   ```bash
   python -m app.cli create-superadmin --email you@uni.edu --name "Your Name"
   ```

Notes:

- Persistent disks require the **Starter** plan. On the free plan the disk is unavailable
  and the database resets on redeploy; point `DATABASE_URL` at a managed Postgres instead.
- Keep exactly one instance. SQLite does not support several writers; move to Postgres
  before scaling horizontally.
- `SESSION_COOKIE_SECURE=1` is already set so the session cookie is HTTPS-only.
- Local Docker is optional; `docker build -t campus-extra-classes .` and
  `docker run -p 8000:8000 campus-extra-classes` reproduce the production image.

## Project layout

```
app/
  main.py              FastAPI app, page routes, template setup
  content.py           hard-coded copy for the public pages
  config.py            environment variables and session settings
  db.py                engine, session factory, declarative base
  models.py            users, profiles, applications, classes, meetings, news, audit log
  schemas.py           request/response models for the JSON API
  services.py          business rules (registration, approvals, classes, news)
  security.py          Argon2 hashing and session tokens
  cli.py               management commands (create the first main admin)
  api/
    deps.py            cookie-session auth and role checks
    auth.py            register, login, logout, me
    admin_applications.py
    students.py        staff-facing student directory
    admins.py          main-admin-facing admin directory and role grants
    classes.py         public catalogue + main-admin writes + weekly slots
    news.py            public news feed, staff publishing
  templates/           base shell, main page, placeholder page
  static/css/style.css design tokens and all page styles
alembic/               migration environment and versions
tests/                 page smoke tests + API tests
.github/workflows/ci.yml
Dockerfile             production image (migrations + uvicorn)
render.yaml            Render Blueprint: service, disk, env vars
.dockerignore
```

## Pages

| Route         | Template      | Purpose                                        | Status      |
| ------------- | ------------- | ---------------------------------------------- | ----------- |
| `/`           | `index.html`  | Main page with news and quick links             | done        |
| `/register`   | `stub.html`   | Student sign-up, sign-in, password reset        | placeholder |
| `/classes`    | `stub.html`   | Search and filter the class catalogue           | placeholder |
| `/my-classes` | `stub.html`   | Personal weekly schedule and enrolment          | placeholder |
| `/admin`      | `stub.html`   | Staff CRUD for classes, capacity and rosters    | placeholder |

The HTML pages are visually owned by another teammate. Data features are exposed as JSON
under `/api` so screens can be wired up without touching templates.

## Data model

| Table                 | Holds                                                                 |
| --------------------- | --------------------------------------------------------------------- |
| `users`               | one account: lowercase-unique email, Argon2 hash, role, status, timestamps |
| `student_profiles`    | student number (unique), faculty, study year, phone (1:1 with a student) |
| `admin_profiles`      | position, department, approver, approval date (created only on approval) |
| `admin_applications`  | request, motivation, status, reviewer, decision note                   |
| `auth_sessions`       | SHA-256 hash of the cookie token, expiry, revocation                   |
| `audit_log`           | append-only trail: who registered, logged in, approved or rejected what |
| `extra_classes`       | code (unique, upper-case), title, description, category, teacher, capacity, draft/published/archived |
| `class_memberships`   | one role per person per club: `visitor` (self-joined) or `member` (promoted by staff) |
| `class_meetings`      | weekly slot per class: weekday 0-6, start/end time, room, note, audience `everyone`/`members` |
| `news_posts`          | title, body, optional club, audience `public`/`members`, author, publication timestamp |

Roles are `student`, `admin` and `superadmin` (the "main admin"). A student self-registers
as `student`; becoming an `admin` happens either through an application approved by a
`superadmin` or through a direct grant by the main admin. Suspended accounts cannot log in.
Only the `superadmin` creates or edits classes; admins and the main admin manage weekly
meeting slots, club memberships and news. Visitors read published classes and public news.

Inside a club a person holds exactly one of two roles: `visitor` or `member`. Anyone signed
in joins a published club as a `visitor` immediately; only staff can promote a visitor to
`member`. A person can never hold both roles in the same club. Members-only meeting slots
and members-only club news are hidden from visitors, outsiders and anonymous readers;
staff still see them for moderation.

## API

| Method | Path                                       | Who may call        |
| ------ | ------------------------------------------ | ------------------- |
| POST   | `/api/auth/register`                       | anyone              |
| POST   | `/api/auth/login`                          | anyone              |
| POST   | `/api/auth/logout`                         | logged in           |
| GET    | `/api/auth/me`                             | logged in           |
| POST   | `/api/admin-applications`                  | student             |
| GET    | `/api/admin-applications/me`               | logged in           |
| GET    | `/api/admin-applications?status=pending`   | main admin          |
| POST   | `/api/admin-applications/{id}/approve`     | main admin          |
| POST   | `/api/admin-applications/{id}/reject`      | main admin          |
| GET    | `/api/students?q=&limit=&offset=`          | admin, main admin   |
| GET    | `/api/students/{id}`                       | admin, main admin   |
| GET    | `/api/admins?q=`                           | main admin          |
| POST   | `/api/admins/grant`                        | main admin          |
| GET    | `/api/classes?q=&category=&status=`        | anyone (status only for staff) |
| GET    | `/api/classes/{id}`                        | anyone (unpublished only for staff) |
| POST   | `/api/classes`                             | main admin          |
| PATCH  | `/api/classes/{id}`                        | main admin          |
| POST   | `/api/classes/{id}/archive`                | main admin          |
| POST   | `/api/classes/{id}/meetings`               | admin, main admin   |
| PATCH  | `/api/classes/{id}/meetings/{meeting_id}`  | admin, main admin   |
| DELETE | `/api/classes/{id}/meetings/{meeting_id}`  | admin, main admin   |
| POST   | `/api/classes/{id}/membership`             | anyone signed in (joins as visitor) |
| GET    | `/api/classes/{id}/memberships?role=`      | admin, main admin   |
| PATCH  | `/api/classes/{id}/memberships/{user_id}`  | admin, main admin   |
| DELETE | `/api/classes/{id}/memberships/{user_id}`  | admin, main admin   |
| GET    | `/api/news?q=&class_id=`                   | anyone (members-only posts filtered by club role) |
| GET    | `/api/news/{id}`                           | anyone with the matching club role |
| POST   | `/api/news`                                | admin, main admin   |
| PATCH  | `/api/news/{id}`                           | admin, main admin   |
| DELETE | `/api/news/{id}`                           | admin, main admin   |

Schema changes always come with a migration:

```bash
alembic revision --autogenerate -m "what changed"
alembic upgrade head
```

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

## Ownership

- **Accounts, profiles, admin approval, class catalogue, meeting slots, news, database** —
  this module.
- **Visual design and page templates** — owned by the frontend teammate. Do not restyle
  pages as a side effect of data work.
- **Search ranking and enrolment** — owned by the search teammate. The catalogue tables and
  keyword/category filters are ready for them; they add enrolments and replace the simple
  `q` filter with real ranking under `app/api/`.

## Roadmap

- [x] Accounts: registration, login, session cookies
- [x] Admin applications with main-admin approval
- [x] Student and admin directories for staff
- [x] Direct admin grants by the main admin
- [x] Class catalogue, weekly meeting slots and campus news (JSON API)
- [x] Club roles: visitor self-join, staff-promoted members, members-only slots and news
- [ ] Search ranking and filters over the catalogue (search teammate)
- [ ] Personal schedule view and enrolment actions
- [ ] Admin UI for classes, CSV export
- [ ] Seed data and a demo account for reviews
