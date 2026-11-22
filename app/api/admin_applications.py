"""Students apply to become admins; the main admin approves or rejects."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import schemas, services
from app.api.deps import get_current_user, require_roles
from app.db import get_db
from app.models import AdminApplication, ApplicationStatus, Role, User

router = APIRouter(prefix="/admin-applications", tags=["admin applications"])


@router.post("", response_model=schemas.AdminApplicationOut, status_code=status.HTTP_201_CREATED)
def submit_application(
    payload: schemas.AdminApplicationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.STUDENT)),
) -> AdminApplication:
    try:
        return services.submit_admin_application(db, user, payload)
    except services.PendingApplicationExists as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a pending application",
        ) from exc


@router.get("/me", response_model=schemas.AdminApplicationList)
def my_applications(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> schemas.AdminApplicationList:
    applications = db.scalars(
        select(AdminApplication)
        .where(AdminApplication.user_id == user.id)
        .order_by(AdminApplication.created_at.desc())
    ).all()
    return schemas.AdminApplicationList(
        items=[schemas.AdminApplicationOut.model_validate(item) for item in applications],
        total=len(applications),
    )


@router.get("", response_model=schemas.AdminApplicationList)
def list_applications(
    status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.SUPERADMIN)),
) -> schemas.AdminApplicationList:
    stmt = select(AdminApplication)
    count_stmt = select(func.count(AdminApplication.id))
    if status_filter is not None:
        stmt = stmt.where(AdminApplication.status == status_filter)
        count_stmt = count_stmt.where(AdminApplication.status == status_filter)

    applications = db.scalars(stmt.order_by(AdminApplication.created_at.desc())).all()
    return schemas.AdminApplicationList(
        items=[schemas.AdminApplicationOut.model_validate(item) for item in applications],
        total=db.scalar(count_stmt) or 0,
    )


@router.post("/{application_id}/approve", response_model=schemas.AdminApplicationOut)
def approve_application(
    application_id: int,
    payload: schemas.DecisionRequest | None = None,
    db: Session = Depends(get_db),
    reviewer: User = Depends(require_roles(Role.SUPERADMIN)),
) -> AdminApplication:
    return _decide(db, application_id, reviewer, approve=True, note=payload.note if payload else None)


@router.post("/{application_id}/reject", response_model=schemas.AdminApplicationOut)
def reject_application(
    application_id: int,
    payload: schemas.DecisionRequest | None = None,
    db: Session = Depends(get_db),
    reviewer: User = Depends(require_roles(Role.SUPERADMIN)),
) -> AdminApplication:
    return _decide(db, application_id, reviewer, approve=False, note=payload.note if payload else None)


def _decide(
    db: Session,
    application_id: int,
    reviewer: User,
    *,
    approve: bool,
    note: str | None,
) -> AdminApplication:
    try:
        return services.decide_application(
            db, application_id, reviewer, approve=approve, note=note
        )
    except services.ApplicationNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
        ) from exc
    except services.ApplicationAlreadyDecided as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This application has already been decided",
        ) from exc
