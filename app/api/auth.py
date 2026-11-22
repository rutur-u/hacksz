"""Registration, login, logout and the current-user endpoint."""

from __future__ import annotations

from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app import schemas, services
from app.api.deps import get_current_user
from app.config import COOKIE_SECURE, SESSION_COOKIE_NAME, SESSION_TTL
from app.db import get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)) -> User:
    try:
        return services.register_student(db, payload)
    except services.EmailAlreadyRegistered as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from exc


@router.post("/login", response_model=schemas.UserOut)
def login(
    payload: schemas.LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    user = services.authenticate(db, str(payload.email), payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token, expires_at = services.create_session(db, user)
    max_age = int(SESSION_TTL.total_seconds())
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=max_age,
        expires=expires_at.replace(tzinfo=timezone.utc),
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        path="/",
    )
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        services.revoke_session(db, token)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


@router.get("/me", response_model=schemas.MeOut)
def me(user: User = Depends(get_current_user)) -> schemas.MeOut:
    return schemas.MeOut.model_validate(
        {
            "user": user,
            "student_profile": user.student_profile,
            "admin_profile": user.admin_profile,
        }
    )
