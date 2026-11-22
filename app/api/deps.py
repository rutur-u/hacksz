"""Shared dependencies: cookie-session authentication and role checks."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import SESSION_COOKIE_NAME
from app.db import get_db
from app.models import AuthSession, Role, User, UserStatus, utcnow
from app.security import hash_token


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Cookie"},
    )
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise unauthorized

    session = db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == hash_token(token),
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > utcnow(),
        )
    )
    if session is None:
        raise unauthorized

    user = db.get(User, session.user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise unauthorized

    session.last_used_at = utcnow()
    db.commit()
    return user


def require_roles(*roles: Role) -> Callable[..., User]:
    """Dependency factory: only the listed roles may reach the endpoint."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return dependency
