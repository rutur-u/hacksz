"""Runtime configuration, read from environment variables.

Every value has a safe development default, so `uvicorn app.main:app --reload`
works on a fresh clone without extra setup.
"""

from __future__ import annotations

import os
from datetime import timedelta

# SQLite by default; point this at Postgres later without touching the code.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Opaque token stored in an HttpOnly cookie and hashed in auth_sessions.
SESSION_COOKIE_NAME = "ec_session"
SESSION_TTL = timedelta(days=14)
COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
