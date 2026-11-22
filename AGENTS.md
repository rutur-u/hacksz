# AGENTS.md

Guidance for AI coding assistants working in this repository. Read it before changing code.

## What this is

A FastAPI + Jinja2 portal for extracurricular classes at a university. The main page and
navigation shell exist; every feature page is a deliberate placeholder. This is a small
student team project, so clarity beats cleverness.

## Commands

| Task        | Command                                        |
| ----------- | ---------------------------------------------- |
| Install     | `pip install -r requirements-dev.txt`           |
| Run         | `uvicorn app.main:app --reload`                 |
| Test        | `pytest`                                        |
| New venv    | `python -m venv .venv`                          |

## Where things live

- `app/main.py` — the only route module today. One function per page.
- `app/content.py` — hard-coded news, navigation and placeholder copy.
- `app/templates/` — `base.html` is the shell; pages extend it.
- `app/static/css/style.css` — design tokens in `:root`, then component styles.
- `tests/test_pages.py` — smoke tests that must keep passing.

## Conventions

- Server-rendered Jinja2 and plain CSS. Do **not** introduce React/Vue/Tailwind, a bundler,
  a CDN stylesheet or a JS framework without team agreement in an issue.
- Reuse `.card`, `.btn`, `.pill`, `.section`, `.stub` and the `icon()` macro before writing
  new CSS or new markup patterns.
- Every user-facing page needs: a route in `app/main.py`, a template, a nav entry when it
  belongs in the header, and a case in `tests/test_pages.py`.
- Python: type hints on public functions, double quotes, 4-space indent, lines under 100 chars.
- Templates: 2-space indent, one block per page, semantic HTML, `aria-current` for the active
  nav item.
- Accessibility: every interactive element is a real link or button, icons are decorative
  (`aria-hidden="true"`), colour is never the only signal.
- No secrets, no `.env` files, no `.venv` or generated files in commits.

## Definition of done

- `pytest` passes.
- Page renders correctly at 1440 px and 390 px widths.
- Placeholder pages still say "Planned" and link back to the main page.
- Commit messages follow Conventional Commits; the PR links its issue.

## Do not

- Do not add a database, authentication or migrations without discussing the data model first.
- Do not redesign the visual system or rename existing CSS classes as a side effect.
- Do not delete the placeholder routes — features replace them in place.
- Do not commit directly to `main`.
