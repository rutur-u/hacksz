# smbuclubs

A portal for extracurricular classes at the university. Students browse the catalogue,
join clubs, get promoted from visitor to member and see their weekly schedule. Staff
publish classes, manage meeting slots, memberships and news.

**Live demo:** <https://campus-extra-classes.onrender.com> · API explorer:
<https://campus-extra-classes.onrender.com/docs>

> **Hackathon result.** End-to-end product: accounts and the admin-approval flow, class
> catalogue with weekly meeting slots, visitor/member club roles, members-only news, an
> admin panel, a RU/EN/ZH interface, ranked catalogue search, and a Docker deployment on
> Render + Neon. 10 tables, 3 Alembic migrations, 40 passing tests. Server-side search
> ranking and enrolment are still owned by the search teammate.
>
> The free Render service sleeps after 15 minutes idle — the first request afterwards can
> take up to a minute.

## Stack

| Layer    | Choice                                                       |
| -------- | ------------------------------------------------------------ |
| Runtime  | Python 3.13                                                  |
| Backend  | FastAPI + Uvicorn                                            |
| Views    | Jinja2 templates + vanilla ES modules (no bundler)            |
| Styling  | Plain CSS with design tokens, no build step or CDN            |
| i18n     | JSON dictionaries for English, Russian and Chinese            |
| Storage  | Neon Postgres in production, SQLite locally; SQLAlchemy 2.0 + Alembic |
| Auth     | Argon2 password hashes, opaque session token in an HttpOnly cookie |
| Deploy   | Docker image on Render (free plan) + Neon Postgres            |
| CI       | GitHub Actions: installs dependencies and runs `pytest`       |
| Tests    | 40 tests: page smoke tests, API permissions and flows         |

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

## Deploy for free (Render + Neon)

The repository ships a `Dockerfile` and a `render.yaml` blueprint. Deployment is additive:
it adds container files only and changes no templates, CSS, routes or API code, so future
frontend and search commits keep working and auto-deploy on every push to `main`.

Free stack: Render's free Docker web service plus a free Neon Postgres. No disk and no
paid plan, and both free tiers work without a credit card.

1. **Neon** — sign up at <https://neon.tech>, create a project, open *Connect* and copy the
   **direct** connection string (the one without `-pooler`). It starts with `postgresql://`.
2. **Render** — sign up with GitHub, then **New → Blueprint**, pick this repository and
   branch `main`. When Render asks for `DATABASE_URL`, paste the Neon string there.
3. Render builds the image, runs `alembic upgrade head` against Neon and starts uvicorn on
   `$PORT`. The `render.yaml` has no disk; the database is Neon.
4. Create the first main admin. Render's free plan has no Shell, so generate an Argon2
   hash locally and insert it in the Neon **SQL Editor**:
   (with the project dependencies installed: `pip install -r requirements-dev.txt`)

   ```powershell
   python -c "import getpass; from app.security import hash_password; print(hash_password(getpass.getpass()))"
   ```

   ```sql
   INSERT INTO users (email, full_name, password_hash, role, status, created_at, updated_at)
   VALUES ('you@uni.edu', 'Your Name', '<paste-the-hash>', 'superadmin', 'active', NOW(), NOW());
   ```

   Then sign in at `/docs` with `POST /api/auth/login`.

Notes:

- The free Render service sleeps after 15 minutes idle; the first request afterwards takes
  roughly a minute to wake it. Neon also suspends idle compute and wakes on the first query.
- Keep exactly one Render instance on the free plan; scale by upgrading the service.
- Auto-deploy from `main` is enabled in `render.yaml`; if a push does not start a build,
  use **Manual Deploy → Deploy latest commit**.
- `SESSION_COOKIE_SECURE=1` is already set so the session cookie is HTTPS-only.
- Prefer SQLite on a persistent disk? Switch `plan` to `starter`, add the `disk` block back
  and point `DATABASE_URL` at `sqlite:////data/app.db`; the history has that variant.
- Local Docker is optional; `docker build -t campus-extra-classes .` and
  `docker run -p 8000:8000 -e DATABASE_URL=... campus-extra-classes` reproduce the image.

## Project layout

```
app/
  main.py              FastAPI app, page routes, locale middleware
  content.py           navigation, quick links and translation keys
  i18n.py              locale resolution and dictionary loading
  locales/             en.json, ru.json, zh.json
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
    classes.py         public catalogue + main-admin writes + weekly slots + memberships
    news.py            public news feed, staff publishing
  templates/           landing, auth, catalogue, class detail, my classes, admin, shell
  static/css/style.css design tokens and all page styles
  static/js/           one ES module per screen, no build step
alembic/               migration environment and 3 versions
tests/                 page smoke tests, API tests and i18n tests
.github/workflows/ci.yml
Dockerfile             production image (migrations + uvicorn)
render.yaml            Render Blueprint: free service, Neon URL, secure cookies
.dockerignore
```

## Pages

| Route           | Template           | Purpose                                         | Status  |
| --------------- | ------------------ | ----------------------------------------------- | ------- |
| `/`             | `index.html`       | Landing page with quick links and news feed      | done    |
| `/register`     | `auth.html`        | Sign up, sign in, session state                  | done    |
| `/classes`      | `classes.html`     | Catalogue with ranked search and filters         | done    |
| `/classes/{id}` | `class_detail.html`| Class page, weekly meetings, join as visitor     | done    |
| `/my-classes`   | `my_classes.html`  | Personal schedule                               | partial — waits for a “my memberships” endpoint |
| `/admin`        | `admin.html`       | Staff panel: classes, slots, members, news       | done    |

Every page is available in English, Russian and Chinese via the header switcher
(`?lang=ru`), and the choice is stored in a cookie. Template copy that is not yet in
`app/locales/` stays in the language the frontend teammate wrote it in.

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

- **Accounts, profiles, admin approval, class catalogue, meeting slots, memberships, news,
  i18n, database and deployment** — this module.
- **Visual design** — created by the frontend teammate and merged; changes to the visual
  system should go through them.
- **Search** — the client-side prefix-first ranking and filters are in place. The search
  teammate still owns server-side relevance ranking and the enrolment tables.

## Roadmap

- [x] Accounts: registration, login, session cookies
- [x] Admin applications with main-admin approval
- [x] Student and admin directories for staff
- [x] Direct admin grants by the main admin
- [x] Class catalogue, weekly meeting slots and campus news (JSON API)
- [x] Club roles: visitor self-join, staff-promoted members, members-only slots and news
- [x] Frontend: landing page, auth, catalogue, class detail, admin panel, dark mode
- [x] RU/EN/ZH interface with cookie persistence
- [x] Ranked catalogue search with category, weekday and status filters
- [x] Docker deployment on Render + Neon Postgres, live demo
- [ ] Server-side relevance ranking and enrolment tables (search teammate)
- [ ] Personal schedule view (`my memberships` endpoint + `/my-classes`)
- [ ] CSV export of class rosters
- [ ] Seed data for demo accounts
