"""Read-only student directory for staff (the analytics base list)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import schemas
from app.api.deps import require_roles
from app.db import get_db
from app.models import Role, StudentProfile, User

router = APIRouter(prefix="/students", tags=["students"])


def _row(user: User) -> schemas.StudentOut:
    profile = (
        schemas.StudentProfileOut.model_validate(user.student_profile)
        if user.student_profile is not None
        else None
    )
    return schemas.StudentOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        status=user.status,
        created_at=user.created_at,
        profile=profile,
    )


@router.get("", response_model=schemas.StudentList)
def list_students(
    q: str | None = Query(default=None, max_length=120, description="Name, email or student number"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.ADMIN, Role.SUPERADMIN)),
) -> schemas.StudentList:
    stmt = (
        select(User)
        .outerjoin(StudentProfile, StudentProfile.user_id == User.id)
        .where(User.role == Role.STUDENT)
    )
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                User.full_name.ilike(pattern),
                User.email.ilike(pattern),
                StudentProfile.student_number.ilike(pattern),
            )
        )

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    users = db.scalars(
        stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
    ).all()
    return schemas.StudentList(items=[_row(user) for user in users], total=total)


@router.get("/{student_id}", response_model=schemas.StudentOut)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.ADMIN, Role.SUPERADMIN)),
) -> schemas.StudentOut:
    user = db.scalar(select(User).where(User.id == student_id, User.role == Role.STUDENT))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return _row(user)
