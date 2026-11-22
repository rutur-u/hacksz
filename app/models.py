"""SQLAlchemy models for accounts, profiles, admin requests and audit trail.

Scope note: the class catalogue, enrolments and search are owned by the search
teammate. Their tables belong in this module too, so imports stay in one place.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    """Naive UTC timestamp; SQLite does not keep timezones."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Role(StrEnum):
    STUDENT = "student"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class UserStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class ApplicationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


def enum_column(enum_class: type[StrEnum], name: str) -> Enum:
    """Store enum values as short strings instead of native database enums."""
    return Enum(
        enum_class,
        native_enum=False,
        length=20,
        values_callable=lambda members: [member.value for member in members],
        name=name,
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(enum_column(Role, "user_role"), default=Role.STUDENT)
    status: Mapped[UserStatus] = mapped_column(
        enum_column(UserStatus, "user_status"), default=UserStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    student_profile: Mapped[StudentProfile | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    admin_profile: Mapped[AdminProfile | None] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="AdminProfile.user_id",
    )


class StudentProfile(Base):
    """Student-specific fields; the academic record lives here, not on User."""

    __tablename__ = "student_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    student_number: Mapped[str | None] = mapped_column(String(32), unique=True)
    faculty: Mapped[str | None] = mapped_column(String(120))
    study_year: Mapped[int | None]
    phone: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped[User] = relationship(back_populates="student_profile")


class AdminProfile(Base):
    """Created only when the main admin approves an application."""

    __tablename__ = "admin_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[str] = mapped_column(String(120))
    department: Mapped[str | None] = mapped_column(String(120))
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    approved_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    note: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="admin_profile", foreign_keys=[user_id])


class AdminApplication(Base):
    """A student asks to become an admin; the main admin decides."""

    __tablename__ = "admin_applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    requested_position: Mapped[str] = mapped_column(String(120))
    department: Mapped[str | None] = mapped_column(String(120))
    motivation: Mapped[str] = mapped_column(Text)
    status: Mapped[ApplicationStatus] = mapped_column(
        enum_column(ApplicationStatus, "application_status"),
        default=ApplicationStatus.PENDING,
        index=True,
    )
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    applicant: Mapped[User] = relationship(foreign_keys=[user_id], lazy="joined")

    __table_args__ = (Index("ix_admin_applications_user_status", "user_id", "status"),)


class AuthSession(Base):
    """One row per logged-in browser. The cookie holds the raw token, never the row."""

    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship()


class AuditLog(Base):
    """Append-only record of sensitive actions (approvals, suspensions)."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(60))
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int | None]
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (Index("ix_audit_log_entity", "entity_type", "entity_id"),)
