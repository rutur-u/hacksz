"""Campus news: anyone may read, admins and the main admin post and edit."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import schemas, services
from app.api.deps import require_roles
from app.db import get_db
from app.models import NewsPost, Role, User

router = APIRouter(prefix="/news", tags=["news"])

STAFF_ROLES = (Role.ADMIN, Role.SUPERADMIN)


@router.get("", response_model=schemas.NewsList)
def list_news(
    q: str | None = Query(default=None, max_length=120, description="Title or body"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> schemas.NewsList:
    stmt = select(NewsPost)
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
def get_news(news_id: int, db: Session = Depends(get_db)) -> NewsPost:
    post = db.get(NewsPost, news_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News not found")
    return post


@router.post("", response_model=schemas.NewsOut, status_code=status.HTTP_201_CREATED)
def create_news(
    payload: schemas.NewsCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*STAFF_ROLES)),
) -> NewsPost:
    return services.create_news(db, actor, payload)


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
