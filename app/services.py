"""Business rules for accounts and the admin-approval flow.

Routers stay thin; anything that must hold true regardless of the caller lives here.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.config import SESSION_TTL
from app.models import (
    AdminApplication,
    AdminProfile,
    ApplicationStatus,
    AuditLog,
    AuthSession,
    Role,
    StudentProfile,
    User,
    UserStatus,
    utcnow,
)
from app.security import hash_password, hash_token, new_session_token, verify_password


class ServiceError(Exception):
    """Base class for expected failures that routers translate into HTTP errors."""


class EmailAlreadyRegistered(ServiceError):
    def __init__(self, email: str) -> None:
        super().__init__(f"Email already registered: {email}")
        self.email = email


class PendingApplicationExists(ServiceError):
    pass


class ApplicationNotFound(ServiceError):
    pass


class ApplicationAlreadyDecided(ServiceError):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _clean(value: str | None) -> str | None:
    """Treat blank optional fields as missing."""
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def log_event(
    db: Session,
    *,
    actor_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None,
    payload: dict[str, object] | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
        )
    )


def register_student(db: Session, payload: schemas.RegisterRequest) -> User:
    email = normalize_email(str(payload.email))
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise EmailAlreadyRegistered(email)

    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=Role.STUDENT,
        status=UserStatus.ACTIVE,
    )
    user.student_profile = StudentProfile(
        student_number=_clean(payload.student_number),
        faculty=_clean(payload.faculty),
        study_year=payload.study_year,
        phone=_clean(payload.phone),
    )
    db.add(user)
    db.flush()
    log_event(
        db,
        actor_id=user.id,
        action="student.registered",
        entity_type="user",
        entity_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None or not verify_password(password, user.password_hash):
        return None
    if user.status != UserStatus.ACTIVE:
        return None
    return user


def create_session(db: Session, user: User) -> tuple[str, datetime]:
    token = new_session_token()
    now = utcnow()
    expires_at = now + SESSION_TTL
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=expires_at,
            last_used_at=now,
        )
    )
    user.last_login_at = now
    log_event(db, actor_id=user.id, action="auth.login", entity_type="user", entity_id=user.id)
    db.commit()
    return token, expires_at


def revoke_session(db: Session, token: str) -> None:
    session = db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == hash_token(token),
            AuthSession.revoked_at.is_(None),
        )
    )
    if session is None:
        return
    session.revoked_at = utcnow()
    log_event(
        db,
        actor_id=session.user_id,
        action="auth.logout",
        entity_type="auth_session",
        entity_id=session.id,
    )
    db.commit()


def submit_admin_application(
    db: Session, user: User, payload: schemas.AdminApplicationCreate
) -> AdminApplication:
    pending = db.scalar(
        select(AdminApplication.id).where(
            AdminApplication.user_id == user.id,
            AdminApplication.status == ApplicationStatus.PENDING,
        )
    )
    if pending is not None:
        raise PendingApplicationExists()

    application = AdminApplication(
        user_id=user.id,
        requested_position=payload.requested_position.strip(),
        department=_clean(payload.department),
        motivation=payload.motivation.strip(),
    )
    db.add(application)
    db.flush()
    log_event(
        db,
        actor_id=user.id,
        action="admin_application.submitted",
        entity_type="admin_application",
        entity_id=application.id,
    )
    db.commit()
    db.refresh(application)
    return application


def decide_application(
    db: Session,
    application_id: int,
    reviewer: User,
    *,
    approve: bool,
    note: str | None,
) -> AdminApplication:
    application = db.get(AdminApplication, application_id)
    if application is None:
        raise ApplicationNotFound(application_id)
    if application.status != ApplicationStatus.PENDING:
        raise ApplicationAlreadyDecided(application_id)

    now = utcnow()
    application.status = ApplicationStatus.APPROVED if approve else ApplicationStatus.REJECTED
    application.reviewed_by_id = reviewer.id
    application.reviewed_at = now
    application.decision_note = _clean(note)

    if approve:
        applicant = application.applicant
        applicant.role = Role.ADMIN
        applicant.status = UserStatus.ACTIVE
        if applicant.admin_profile is None:
            applicant.admin_profile = AdminProfile(
                position=application.requested_position,
                department=application.department,
                approved_by_id=reviewer.id,
                approved_at=now,
                note=application.decision_note,
            )
        else:
            applicant.admin_profile.position = application.requested_position
            applicant.admin_profile.approved_by_id = reviewer.id
            applicant.admin_profile.approved_at = now

    log_event(
        db,
        actor_id=reviewer.id,
        action="admin_application.approved" if approve else "admin_application.rejected",
        entity_type="admin_application",
        entity_id=application.id,
        payload={"user_id": application.user_id},
    )
    db.commit()
    db.refresh(application)
    return application
