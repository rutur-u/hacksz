"""Admin directory and direct role grants, visible to the main admin only."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import schemas, services
from app.api.deps import require_roles
from app.db import get_db
from app.models import AdminProfile, Role, User

router = APIRouter(prefix="/admins", tags=["admins"])


def _row(user: User) -> schemas.AdminOut:
    return schemas.AdminOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        status=user.status,
        created_at=user.created_at,
        profile=(
            schemas.AdminProfileOut.model_validate(user.admin_profile)
            if user.admin_profile is not None
            else None
        ),
    )


@router.get("", response_model=schemas.AdminList)
def list_admins(
    q: str | None = Query(default=None, max_length=120, description="Name or email"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.SUPERADMIN)),
) -> schemas.AdminList:
    stmt = (
        select(User)
        .outerjoin(AdminProfile, AdminProfile.user_id == User.id)
        .where(or_(User.role == Role.ADMIN, User.role == Role.SUPERADMIN))
    )
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(or_(User.full_name.ilike(pattern), User.email.ilike(pattern)))

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    users = db.scalars(
        stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
    ).all()
    return schemas.AdminList(items=[_row(user) for user in users], total=total)


@router.post("/grant", response_model=schemas.AdminOut, status_code=status.HTTP_201_CREATED)
def grant_admin(
    payload: schemas.AdminGrantRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(Role.SUPERADMIN)),
) -> schemas.AdminOut:
    """Promote a person to admin directly, skipping the application queue."""
    try:
        user = services.grant_admin(db, payload.user_id, actor, payload)
    except services.UserNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        ) from exc
    except services.AlreadyAdmin as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User is already an admin"
        ) from exc
    except services.CannotGrantRole as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This role cannot be granted",
        ) from exc
    return _row(user)
