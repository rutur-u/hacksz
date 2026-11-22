"""Management commands.

Create the first main admin (superadmin) before anyone can approve admin requests::

    python -m app.cli create-superadmin --email boss@uni.edu --name "Main Admin"
"""

from __future__ import annotations

import argparse
import getpass
import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Role, User, UserStatus
from app.security import hash_password
from app.services import normalize_email


def create_superadmin(email: str, full_name: str, password: str) -> User:
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == normalize_email(email)))
        if existing is not None:
            raise SystemExit(f"An account with {email} already exists")

        user = User(
            email=normalize_email(email),
            full_name=full_name.strip(),
            password_hash=hash_password(password),
            role=Role.SUPERADMIN,
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


def _prompt_password() -> str:
    password = getpass.getpass("Password: ")
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters")
    if password != getpass.getpass("Repeat password: "):
        raise SystemExit("Passwords do not match")
    return password


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Management commands")
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed = subparsers.add_parser("create-superadmin", help="Create the main admin account")
    seed.add_argument("--email", required=True)
    seed.add_argument("--name", required=True, dest="full_name")
    seed.add_argument("--password", help="Omit to be prompted securely")

    args = parser.parse_args(argv)
    if args.command == "create-superadmin":
        user = create_superadmin(args.email, args.full_name, args.password or _prompt_password())
        print(f"Superadmin created: {user.email} (id={user.id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
