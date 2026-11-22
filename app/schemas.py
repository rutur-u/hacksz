"""Request and response models for the JSON API."""

from __future__ import annotations

from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models import (
    ApplicationStatus,
    ClassStatus,
    ClubRole,
    MeetingAudience,
    NewsAudience,
    Role,
    UserStatus,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    student_number: str | None = Field(default=None, max_length=32)
    faculty: str | None = Field(default=None, max_length=120)
    study_year: int | None = Field(default=None, ge=1, le=8)
    phone: str | None = Field(default=None, max_length=32)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class StudentProfileOut(ORMModel):
    student_number: str | None
    faculty: str | None
    study_year: int | None
    phone: str | None


class AdminProfileOut(ORMModel):
    position: str
    department: str | None
    approved_by_id: int | None
    approved_at: datetime
    note: str | None


class UserOut(ORMModel):
    id: int
    email: str
    full_name: str
    role: Role
    status: UserStatus
    created_at: datetime
    last_login_at: datetime | None


class MeOut(BaseModel):
    user: UserOut
    student_profile: StudentProfileOut | None = None
    admin_profile: AdminProfileOut | None = None


class StudentOut(BaseModel):
    id: int
    email: str
    full_name: str
    status: UserStatus
    created_at: datetime
    profile: StudentProfileOut | None = None


class StudentList(BaseModel):
    items: list[StudentOut]
    total: int


class AdminOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: Role
    status: UserStatus
    created_at: datetime
    profile: AdminProfileOut | None = None


class AdminList(BaseModel):
    items: list[AdminOut]
    total: int


class AdminApplicationCreate(BaseModel):
    requested_position: str = Field(min_length=2, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    motivation: str = Field(min_length=10, max_length=2000)


class DecisionRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class AdminApplicationOut(ORMModel):
    id: int
    user_id: int
    requested_position: str
    department: str | None
    motivation: str
    status: ApplicationStatus
    reviewed_by_id: int | None
    reviewed_at: datetime | None
    decision_note: str | None
    created_at: datetime
    applicant: UserOut


class AdminApplicationList(BaseModel):
    items: list[AdminApplicationOut]
    total: int


class AdminGrantRequest(BaseModel):
    """The main admin promotes someone directly, without an application."""

    user_id: int = Field(ge=1)
    position: str = Field(default="Administrator", min_length=2, max_length=120)
    department: str | None = Field(default=None, max_length=120)


class MeetingCreate(BaseModel):
    weekday: int = Field(ge=0, le=6, description="0 = Monday, 6 = Sunday")
    start_time: time
    end_time: time
    room: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=500)
    audience: MeetingAudience = MeetingAudience.EVERYONE

    @model_validator(mode="after")
    def _end_after_start(self) -> MeetingCreate:
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be later than start_time")
        return self


class MeetingUpdate(BaseModel):
    weekday: int | None = Field(default=None, ge=0, le=6)
    start_time: time | None = None
    end_time: time | None = None
    room: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=500)
    audience: MeetingAudience | None = None


class MeetingOut(ORMModel):
    id: int
    class_id: int
    weekday: int
    start_time: time
    end_time: time
    room: str | None
    note: str | None
    audience: MeetingAudience


class ClassCreate(BaseModel):
    code: str = Field(
        min_length=2,
        max_length=32,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$",
        description="Short public identifier, stored upper-case",
    )
    title: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    category: str | None = Field(default=None, max_length=80)
    teacher_name: str = Field(min_length=2, max_length=120)
    capacity: int | None = Field(default=None, ge=1, le=1000)
    status: ClassStatus = ClassStatus.DRAFT


class ClassUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    category: str | None = Field(default=None, max_length=80)
    teacher_name: str | None = Field(default=None, min_length=2, max_length=120)
    capacity: int | None = Field(default=None, ge=1, le=1000)
    status: ClassStatus | None = None


class ClassOut(ORMModel):
    id: int
    code: str
    title: str
    description: str | None
    category: str | None
    teacher_name: str
    capacity: int | None
    status: ClassStatus
    created_by_id: int | None
    created_at: datetime
    updated_at: datetime
    meetings: list[MeetingOut]


class ClassList(BaseModel):
    items: list[ClassOut]
    total: int


class MembershipRoleUpdate(BaseModel):
    role: ClubRole


class MembershipOut(ORMModel):
    id: int
    class_id: int
    user_id: int
    role: ClubRole
    created_at: datetime
    updated_at: datetime
    user: UserOut


class MembershipList(BaseModel):
    items: list[MembershipOut]
    total: int


class NewsCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    body: str = Field(min_length=10, max_length=20000)
    class_id: int | None = Field(default=None, ge=1)
    audience: NewsAudience = NewsAudience.PUBLIC

    @model_validator(mode="after")
    def _members_news_needs_a_club(self) -> NewsCreate:
        if self.audience == NewsAudience.MEMBERS and self.class_id is None:
            raise ValueError("class_id is required for members-only news")
        return self


class NewsUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    body: str | None = Field(default=None, min_length=10, max_length=20000)
    class_id: int | None = Field(default=None, ge=1)
    audience: NewsAudience | None = None


class NewsOut(ORMModel):
    id: int
    title: str
    body: str
    class_id: int | None
    audience: NewsAudience
    author_id: int | None
    published_at: datetime
    created_at: datetime
    updated_at: datetime


class NewsList(BaseModel):
    items: list[NewsOut]
    total: int
