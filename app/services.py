"""Business rules for accounts, the admin-approval flow, classes and news.

Routers stay thin; anything that must hold true regardless of the caller lives here.
"""

from __future__ import annotations

from datetime import datetime, time

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
    ClassMeeting,
    ClassStatus,
    ExtraClass,
    NewsPost,
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


class ClassCodeTaken(ServiceError):
    def __init__(self, code: str) -> None:
        super().__init__(f"Class code already in use: {code}")
        self.code = code


class ClassNotFound(ServiceError):
    pass


class MeetingNotFound(ServiceError):
    pass


class MeetingSlotTaken(ServiceError):
    pass


class InvalidMeetingTime(ServiceError):
    pass


class NewsNotFound(ServiceError):
    pass


class UserNotFound(ServiceError):
    pass


class AlreadyAdmin(ServiceError):
    pass


class CannotGrantRole(ServiceError):
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


def grant_admin(
    db: Session, target_user_id: int, actor: User, payload: schemas.AdminGrantRequest
) -> User:
    """The main admin promotes a person directly, without an application."""
    user = db.get(User, target_user_id)
    if user is None:
        raise UserNotFound(target_user_id)
    if user.role == Role.SUPERADMIN:
        raise CannotGrantRole()
    if user.role == Role.ADMIN:
        raise AlreadyAdmin(target_user_id)

    now = utcnow()
    user.role = Role.ADMIN
    user.admin_profile = AdminProfile(
        position=payload.position.strip(),
        department=_clean(payload.department),
        approved_by_id=actor.id,
        approved_at=now,
        note="Granted directly by the main admin",
    )
    log_event(
        db,
        actor_id=actor.id,
        action="admin.granted",
        entity_type="user",
        entity_id=user.id,
        payload={"position": user.admin_profile.position},
    )
    db.commit()
    db.refresh(user)
    return user


def create_class(db: Session, actor: User, payload: schemas.ClassCreate) -> ExtraClass:
    code = payload.code.strip().upper()
    if db.scalar(select(ExtraClass.id).where(ExtraClass.code == code)) is not None:
        raise ClassCodeTaken(code)

    course = ExtraClass(
        code=code,
        title=payload.title.strip(),
        description=_clean(payload.description),
        category=_clean(payload.category),
        teacher_name=payload.teacher_name.strip(),
        capacity=payload.capacity,
        status=payload.status,
        created_by_id=actor.id,
    )
    db.add(course)
    db.flush()
    log_event(
        db,
        actor_id=actor.id,
        action="class.created",
        entity_type="extra_class",
        entity_id=course.id,
        payload={"code": code},
    )
    db.commit()
    db.refresh(course)
    return course


def update_class(
    db: Session, class_id: int, actor: User, payload: schemas.ClassUpdate
) -> ExtraClass:
    course = db.get(ExtraClass, class_id)
    if course is None:
        raise ClassNotFound(class_id)

    changes = payload.model_dump(exclude_unset=True)
    changes = {
        field: value
        for field, value in changes.items()
        if not (value is None and field in ("title", "teacher_name", "status"))
    }
    for field in ("title", "teacher_name"):
        if changes.get(field) is not None:
            changes[field] = changes[field].strip()
    for field in ("description", "category"):
        if field in changes:
            changes[field] = _clean(changes[field])

    for field, value in changes.items():
        setattr(course, field, value)

    log_event(
        db,
        actor_id=actor.id,
        action="class.updated",
        entity_type="extra_class",
        entity_id=course.id,
        payload={"fields": sorted(changes)},
    )
    db.commit()
    db.refresh(course)
    return course


def archive_class(db: Session, class_id: int, actor: User) -> ExtraClass:
    course = db.get(ExtraClass, class_id)
    if course is None:
        raise ClassNotFound(class_id)
    if course.status == ClassStatus.ARCHIVED:
        return course

    course.status = ClassStatus.ARCHIVED
    log_event(
        db,
        actor_id=actor.id,
        action="class.archived",
        entity_type="extra_class",
        entity_id=course.id,
    )
    db.commit()
    db.refresh(course)
    return course


def _get_class_or_raise(db: Session, class_id: int) -> ExtraClass:
    course = db.get(ExtraClass, class_id)
    if course is None:
        raise ClassNotFound(class_id)
    return course


def _validate_times(start: time, end: time) -> None:
    if end <= start:
        raise InvalidMeetingTime()


def _ensure_slot_free(
    db: Session,
    class_id: int,
    weekday: int,
    start_time: time,
    *,
    exclude_id: int | None = None,
) -> None:
    stmt = select(ClassMeeting.id).where(
        ClassMeeting.class_id == class_id,
        ClassMeeting.weekday == weekday,
        ClassMeeting.start_time == start_time,
    )
    if exclude_id is not None:
        stmt = stmt.where(ClassMeeting.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise MeetingSlotTaken()


def create_meeting(
    db: Session, class_id: int, actor: User, payload: schemas.MeetingCreate
) -> ClassMeeting:
    _get_class_or_raise(db, class_id)
    _validate_times(payload.start_time, payload.end_time)
    _ensure_slot_free(db, class_id, payload.weekday, payload.start_time)

    meeting = ClassMeeting(
        class_id=class_id,
        weekday=payload.weekday,
        start_time=payload.start_time,
        end_time=payload.end_time,
        room=_clean(payload.room),
        note=_clean(payload.note),
    )
    db.add(meeting)
    db.flush()
    log_event(
        db,
        actor_id=actor.id,
        action="class_meeting.created",
        entity_type="class_meeting",
        entity_id=meeting.id,
        payload={"class_id": class_id},
    )
    db.commit()
    db.refresh(meeting)
    return meeting


def update_meeting(
    db: Session, class_id: int, meeting_id: int, actor: User, payload: schemas.MeetingUpdate
) -> ClassMeeting:
    _get_class_or_raise(db, class_id)
    meeting = db.scalar(
        select(ClassMeeting).where(
            ClassMeeting.id == meeting_id, ClassMeeting.class_id == class_id
        )
    )
    if meeting is None:
        raise MeetingNotFound(meeting_id)

    changes = payload.model_dump(exclude_unset=True)
    changes = {
        field: value
        for field, value in changes.items()
        if not (value is None and field in ("weekday", "start_time", "end_time"))
    }
    start = changes.get("start_time", meeting.start_time)
    end = changes.get("end_time", meeting.end_time)
    weekday = changes.get("weekday", meeting.weekday)
    _validate_times(start, end)
    if weekday != meeting.weekday or start != meeting.start_time:
        _ensure_slot_free(db, class_id, weekday, start, exclude_id=meeting.id)

    for field in ("room", "note"):
        if field in changes:
            changes[field] = _clean(changes[field])
    for field, value in changes.items():
        setattr(meeting, field, value)

    log_event(
        db,
        actor_id=actor.id,
        action="class_meeting.updated",
        entity_type="class_meeting",
        entity_id=meeting.id,
        payload={"class_id": class_id, "fields": sorted(changes)},
    )
    db.commit()
    db.refresh(meeting)
    return meeting


def delete_meeting(db: Session, class_id: int, meeting_id: int, actor: User) -> None:
    meeting = db.scalar(
        select(ClassMeeting).where(
            ClassMeeting.id == meeting_id, ClassMeeting.class_id == class_id
        )
    )
    if meeting is None:
        raise MeetingNotFound(meeting_id)

    log_event(
        db,
        actor_id=actor.id,
        action="class_meeting.deleted",
        entity_type="class_meeting",
        entity_id=meeting.id,
        payload={"class_id": class_id},
    )
    db.delete(meeting)
    db.commit()


def create_news(db: Session, actor: User, payload: schemas.NewsCreate) -> NewsPost:
    post = NewsPost(
        title=payload.title.strip(),
        body=payload.body.strip(),
        author_id=actor.id,
        published_at=utcnow(),
    )
    db.add(post)
    db.flush()
    log_event(
        db,
        actor_id=actor.id,
        action="news.published",
        entity_type="news_post",
        entity_id=post.id,
    )
    db.commit()
    db.refresh(post)
    return post


def update_news(
    db: Session, news_id: int, actor: User, payload: schemas.NewsUpdate
) -> NewsPost:
    post = db.get(NewsPost, news_id)
    if post is None:
        raise NewsNotFound(news_id)

    changes = payload.model_dump(exclude_unset=True)
    changes = {
        field: value
        for field, value in changes.items()
        if not (value is None and field in ("title", "body"))
    }
    for field in ("title", "body"):
        if changes.get(field) is not None:
            changes[field] = changes[field].strip()
    for field, value in changes.items():
        setattr(post, field, value)

    log_event(
        db,
        actor_id=actor.id,
        action="news.updated",
        entity_type="news_post",
        entity_id=post.id,
        payload={"fields": sorted(changes)},
    )
    db.commit()
    db.refresh(post)
    return post


def delete_news(db: Session, news_id: int, actor: User) -> None:
    post = db.get(NewsPost, news_id)
    if post is None:
        raise NewsNotFound(news_id)

    log_event(
        db,
        actor_id=actor.id,
        action="news.deleted",
        entity_type="news_post",
        entity_id=post.id,
    )
    db.delete(post)
    db.commit()
