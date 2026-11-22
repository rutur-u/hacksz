"""Campus and club news: public posts for everyone, members-only posts per club."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app import schemas, services
from app.api.deps import get_optional_user, require_roles
from app.db import get_db
from app.models import (
    ClassMembership,
    ClubRole,
    NewsAudience,
    NewsPost,
    Role,
    User,
)

router = APIRouter(prefix="/news", tags=["news"])

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


def _visible_filter(user: User | None):
    """Only public posts, plus members-only posts of clubs the viewer belongs to."""
    if _is_staff(user):
        return None
    conditions = [NewsPost.audience == NewsAudience.PUBLIC]
    if user is not None:
        member_class_ids = select(ClassMembership.class_id).where(
            ClassMembership.user_id == user.id,
            ClassMembership.role == ClubRole.MEMBER,
        )
        conditions.append(
            and_(
                NewsPost.audience == NewsAudience.MEMBERS,
                NewsPost.class_id.in_(member_class_ids),
            )
        )
    return or_(*conditions)


@router.get("", response_model=schemas.NewsList)
def list_news(
    q: str | None = Query(default=None, max_length=120, description="Title or body"),
    class_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> schemas.NewsList:
    stmt = select(NewsPost)
    visibility = _visible_filter(user)
    if visibility is not None:
        stmt = stmt.where(visibility)
    if class_id is not None:
        stmt = stmt.where(NewsPost.class_id == class_id)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(or_(NewsPost.title.ilike(pattern), NewsPost.body.ilike(pattern)))

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    posts = db.scalars(
        stmt.order_by(NewsPost.published_at.desc()).limit(limit).offset(offset)
    ).all()
    return schemas.NewsList(
        items=[schemas.NewsOut.model_validate(post) for post in posts],
        total=total,
    )


@router.get("/{news_id}", response_model=schemas.NewsOut)
def get_news(
    news_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> NewsPost:
    post = db.get(NewsPost, news_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News not found")

    if post.audience == NewsAudience.MEMBERS and not _is_staff(user):
        allowed = (
            user is not None
            and post.class_id is not None
            and post.class_id in _member_class_ids(db, user)
        )
        if not allowed:
            # Outsiders should not learn that a members-only post exists.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="News not found"
            )
    return post


@router.post("", response_model=schemas.NewsOut, status_code=status.HTTP_201_CREATED)
def create_news(
    payload: schemas.NewsCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*STAFF_ROLES)),
) -> NewsPost:
    try:
        return services.create_news(db, actor, payload)
    except services.ClassNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Class not found"
        ) from exc
    except services.InvalidNewsAudience as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="class_id is required for members-only news",
        ) from exc


@router.patch("/{news_id}", response_model=schemas.NewsOut)
def update_news(
    news_id: int,
    payload: schemas.NewsUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*STAFF_ROLES)),
) -> NewsPost:
    try:
        return services.update_news(db, news_id, actor, payload)
    except services.NewsNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="News not found"
        ) from exc
    except services.ClassNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Class not found"
        ) from exc
    except services.InvalidNewsAudience as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="class_id is required for members-only news",
        ) from exc


@router.delete("/{news_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_news(
    news_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*STAFF_ROLES)),
) -> None:
    try:
        services.delete_news(db, news_id, actor)
    except services.NewsNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="News not found"
        ) from exc
