"""Admin directory, visible to the main admin only."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import schemas
from app.api.deps import require_roles
from app.db import get_db
from app.models import AdminProfile, Role, User

router = APIRouter(prefix="/admins", tags=["admins"])


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
    items = [
        schemas.AdminOut(
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
        for user in users
    ]
    return schemas.AdminList(items=items, total=total)
