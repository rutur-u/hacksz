"""Request and response models for the JSON API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import ApplicationStatus, Role, UserStatus


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
