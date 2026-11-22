"""Password hashing and opaque session tokens."""

from __future__ import annotations

import hashlib
import secrets

from pwdlib import PasswordHash

_password_hash = PasswordHash.recommended()


def hash_password(raw_password: str) -> str:
    return _password_hash.hash(raw_password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    try:
        return _password_hash.verify(raw_password, password_hash)
    except Exception:  # malformed hash in the database: treat as a failed login
        return False


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Session tokens are stored hashed, so a database leak cannot be replayed."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
