"""Class catalogue: public read, main-admin writes, staff-managed weekly slots."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import schemas, services
from app.api.deps import get_current_user, get_optional_user, require_roles
from app.db import get_db
from app.models import (
    ClassMembership,
    ClassStatus,
    ClubRole,
    ExtraClass,
    MeetingAudience,
    Role,
    User,
)

router = APIRouter(prefix="/classes", tags=["classes"])

STAFF_ROLES = (Role.ADMIN, Role.SUPERADMIN)


def _is_staff(user: User | None) -> bool:
    return user is not None and user.role in STAFF_ROLES


def _member_class_ids(db: Session, user: User | None) -> set[int]:
    if user is None:
        return set()
    return set(
        db.scalars(
            select(ClassMembership.class_id).where(
                ClassMembership.user_id == user.id,
                ClassMembership.role == ClubRole.MEMBER,
            )
        ).all()
    )


def _can_see_meeting(
    meeting: schemas.MeetingOut, user: User | None, member_class_ids: set[int]
) -> bool:
    if meeting.audience == MeetingAudience.EVERYONE:
        return True
    if user is None:
        return False
    if _is_staff(user):
        return True
    return meeting.class_id in member_class_ids


def _class_out(
    course: ExtraClass, user: User | None, member_class_ids: set[int]
) -> schemas.ClassOut:
    payload = schemas.ClassOut.model_validate(course)
    payload.meetings = [
        meeting
        for meeting in payload.meetings
        if _can_see_meeting(meeting, user, member_class_ids)
    ]
    return payload


@router.get("", response_model=schemas.ClassList)
def list_classes(
    q: str | None = Query(default=None, max_length=120, description="Code, title or teacher"),
    category: str | None = Query(default=None, max_length=80),
    status_filter: ClassStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> schemas.ClassList:
    stmt = select(ExtraClass)
    if _is_staff(user):
        if status_filter is not None:
            stmt = stmt.where(ExtraClass.status == status_filter)
    else:
        # Visitors and students only ever see the published catalogue.
        stmt = stmt.where(ExtraClass.status == ClassStatus.PUBLISHED)

    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                ExtraClass.code.ilike(pattern),
                ExtraClass.title.ilike(pattern),
                ExtraClass.teacher_name.ilike(pattern),
                ExtraClass.description.ilike(pattern),
            )
        )
    if category:
        stmt = stmt.where(ExtraClass.category == category.strip())

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    classes = db.scalars(
        stmt.order_by(ExtraClass.created_at.desc()).limit(limit).offset(offset)
    ).all()
    member_class_ids = _member_class_ids(db, user)
    return schemas.ClassList(
        items=[_class_out(course, user, member_class_ids) for course in classes],
        total=total,
    )


@router.get("/{class_id}", response_model=schemas.ClassOut)
def get_class(
    class_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> schemas.ClassOut:
    course = db.get(ExtraClass, class_id)
    if course is None or (
        course.status != ClassStatus.PUBLISHED and not _is_staff(user)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    return _class_out(course, user, _member_class_ids(db, user))


@router.post("", response_model=schemas.ClassOut, status_code=status.HTTP_201_CREATED)
def create_class(
    payload: schemas.ClassCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(Role.SUPERADMIN)),
) -> ExtraClass:
    try:
        return services.create_class(db, actor, payload)
    except services.ClassCodeTaken as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Class code {exc.code} is already in use",
        ) from exc


@router.patch("/{class_id}", response_model=schemas.ClassOut)
def update_class(
    class_id: int,
    payload: schemas.ClassUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(Role.SUPERADMIN)),
) -> ExtraClass:
    try:
        return services.update_class(db, class_id, actor, payload)
    except services.ClassNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Class not found"
        ) from exc


@router.post("/{class_id}/archive", response_model=schemas.ClassOut)
def archive_class(
    class_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(Role.SUPERADMIN)),
) -> ExtraClass:
    try:
        return services.archive_class(db, class_id, actor)
    except services.ClassNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Class not found"
        ) from exc


@router.post(
    "/{class_id}/meetings",
    response_model=schemas.MeetingOut,
    status_code=status.HTTP_201_CREATED,
)
def create_meeting(
    class_id: int,
    payload: schemas.MeetingCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*STAFF_ROLES)),
) -> schemas.MeetingOut:
    try:
        return services.create_meeting(db, class_id, actor, payload)
    except services.ClassNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Class not found"
        ) from exc
    except services.MeetingSlotTaken as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This class already has a slot starting at that time",
        ) from exc


@router.patch("/{class_id}/meetings/{meeting_id}", response_model=schemas.MeetingOut)
def update_meeting(
    class_id: int,
    meeting_id: int,
    payload: schemas.MeetingUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*STAFF_ROLES)),
) -> schemas.MeetingOut:
    try:
        return services.update_meeting(db, class_id, meeting_id, actor, payload)
    except services.ClassNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Class not found"
        ) from exc
    except services.MeetingNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found"
        ) from exc
    except services.MeetingSlotTaken as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This class already has a slot starting at that time",
        ) from exc
    except services.InvalidMeetingTime as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_time must be later than start_time",
        ) from exc


@router.delete("/{class_id}/meetings/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(
    class_id: int,
    meeting_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*STAFF_ROLES)),
) -> None:
    try:
        services.delete_meeting(db, class_id, meeting_id, actor)
    except services.MeetingNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found"
        ) from exc


@router.post(
    "/{class_id}/membership",
    response_model=schemas.MembershipOut,
    status_code=status.HTTP_201_CREATED,
)
def join_class(
    class_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> schemas.MembershipOut:
    """Anyone signed in may join a published club as a visitor."""
    try:
        return services.join_class(db, class_id, user)
    except services.ClassNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Class not found"
        ) from exc
    except services.ClassNotJoinable as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This class is not open for joining",
        ) from exc
    except services.MembershipExists as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a role in this class",
        ) from exc


@router.get("/{class_id}/memberships", response_model=schemas.MembershipList)
def list_memberships(
    class_id: int,
    role_filter: ClubRole | None = Query(default=None, alias="role"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*STAFF_ROLES)),
) -> schemas.MembershipList:
    if db.get(ExtraClass, class_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

    stmt = select(ClassMembership).where(ClassMembership.class_id == class_id)
    if role_filter is not None:
        stmt = stmt.where(ClassMembership.role == role_filter)
    memberships = db.scalars(stmt.order_by(ClassMembership.created_at)).all()
    return schemas.MembershipList(
        items=[schemas.MembershipOut.model_validate(item) for item in memberships],
        total=len(memberships),
    )


@router.patch("/{class_id}/memberships/{user_id}", response_model=schemas.MembershipOut)
def set_membership_role(
    class_id: int,
    user_id: int,
    payload: schemas.MembershipRoleUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*STAFF_ROLES)),
) -> schemas.MembershipOut:
    """Staff promote a visitor to member, or move a member back to visitor."""
    try:
        return services.set_membership_role(db, class_id, user_id, actor, payload.role)
    except services.ClassNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Class not found"
        ) from exc
    except services.MembershipNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found"
        ) from exc


@router.delete("/{class_id}/memberships/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_membership(
    class_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*STAFF_ROLES)),
) -> None:
    try:
        services.remove_membership(db, class_id, user_id, actor)
    except services.MembershipNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found"
        ) from exc
