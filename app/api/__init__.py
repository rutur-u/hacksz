"""JSON API mounted under /api; the HTML pages stay untouched."""

from fastapi import APIRouter

from app.api import admin_applications, admins, auth, classes, news, students

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(admin_applications.router)
api_router.include_router(students.router)
api_router.include_router(admins.router)
api_router.include_router(classes.router)
api_router.include_router(news.router)
