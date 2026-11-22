"""Static content for the skeleton build.

Everything here is hard-coded on purpose: the first milestone is the main page
plus the navigation shell. Replace these structures with database queries once
the models and repositories exist.
"""

from __future__ import annotations

from datetime import date
from typing import Any

SITE_NAME = "Campus Extra Classes"

NAV: list[dict[str, str]] = [
    {"key": "home", "label": "Home", "url": "/"},
    {"key": "search", "label": "Find a class", "url": "/classes"},
    {"key": "my_classes", "label": "My classes", "url": "/my-classes"},
    {"key": "admin", "label": "Admin", "url": "/admin"},
]

QUICK_LINKS: list[dict[str, str]] = [
    {
        "key": "register",
        "icon": "user",
        "eyebrow": "Account",
        "title": "Register",
        "body": "Create a student account so you can join classes and keep everything in one place.",
        "url": "/register",
    },
    {
        "key": "search",
        "icon": "search",
        "eyebrow": "Discover",
        "title": "Find a class",
        "body": "Browse every extra class on campus by name, category, teacher or weekday.",
        "url": "/classes",
    },
    {
        "key": "my_classes",
        "icon": "calendar",
        "eyebrow": "Schedule",
        "title": "My classes",
        "body": "See the classes you joined, when and where they meet, and leave a class again.",
        "url": "/my-classes",
    },
    {
        "key": "admin",
        "icon": "shield",
        "eyebrow": "Staff",
        "title": "Class administration",
        "body": "Publish new classes, edit schedules, manage capacity and export rosters.",
        "url": "/admin",
    },
]

NEWS: list[dict[str, Any]] = [
    {
        "date": date(2026, 11, 20),
        "tag": "Portal",
        "title": "The extra-class portal is taking shape",
        "body": (
            "The main page and navigation are in place. Registration, search and "
            "administration screens are being built by the team right now."
        ),
    },
    {
        "date": date(2026, 11, 14),
        "tag": "Registration",
        "title": "Spring enrolment opens in two weeks",
        "body": (
            "Twenty-three extra classes will be offered next term, from robotics to "
            "chamber choir. The catalogue will appear here once staff publish it."
        ),
    },
    {
        "date": date(2026, 11, 6),
        "tag": "Guide",
        "title": "How to choose an extra class",
        "body": (
            "You may join up to three extra classes per term. Check the weekday and "
            "room before enrolling: most courses run once a week for ninety minutes."
        ),
    },
]

STUB_PAGES: dict[str, dict[str, Any]] = {
    "register": {
        "nav": "register",
        "icon": "user",
        "title": "Registration",
        "lead": "Student accounts are not available yet. This page will hold sign-up, sign-in and password recovery.",
        "planned": [
            "Sign up with a university email address",
            "Email verification and password rules",
            "Sign in, sign out and password reset",
        ],
    },
    "search": {
        "nav": "search",
        "icon": "search",
        "title": "Find a class",
        "lead": "The class catalogue is being collected. Search will live here once classes are published by staff.",
        "planned": [
            "List every published extra class",
            "Filter by category, weekday and availability",
            "Open a class page with description, room and teacher",
        ],
    },
    "my_classes": {
        "nav": "my_classes",
        "icon": "calendar",
        "title": "My classes",
        "lead": "Your personal schedule appears here once accounts and enrolment exist.",
        "planned": [
            "Weekly timetable of the classes you joined",
            "Seat counter and enrolment status per class",
            "Leave a class and join the waiting list",
        ],
    },
    "admin": {
        "nav": "admin",
        "icon": "shield",
        "title": "Class administration",
        "lead": "Staff tools are not connected yet. This area will be restricted to administrators.",
        "planned": [
            "Create, edit and archive extra classes",
            "Manage capacity, rooms and weekly schedule",
            "Export rosters as CSV",
        ],
    },
}
