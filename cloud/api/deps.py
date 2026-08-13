"""Auth dependencies for PeekNook Cloud."""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import ApiKey, Subscription, User

JWT_SECRET = os.getenv("JWT_SECRET", "peeknook-cloud-dev-secret-change-me-32b")
JWT_ALG = "HS256"
JWT_EXPIRE_DAYS = 30


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(user_id: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS)
    return jwt.encode({"sub": user_id, "exp": exp}, JWT_SECRET, algorithm=JWT_ALG)


def get_user_from_jwt(
    authorization: Optional[str],
    db: Session,
) -> Optional[User]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        user_id = payload.get("sub")
    except jwt.PyJWTError:
        return None
    return db.get(User, user_id)


def get_user_from_api_key(
    api_key: Optional[str],
    db: Session,
) -> Optional[User]:
    if not api_key or not api_key.startswith("pk_"):
        return None
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    record = db.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash))
    if not record:
        return None
    return db.get(User, record.user_id)


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    x_peeknook_api_key: Optional[str] = Header(default=None, alias="X-PeekNook-Api-Key"),
    db: Session = Depends(get_db),
) -> User:
    user = get_user_from_jwt(authorization, db) or get_user_from_api_key(x_peeknook_api_key, db)
    if not user:
        raise HTTPException(401, "Missing or invalid credentials")
    return user


def ensure_subscription(user: User, db: Session) -> Subscription:
    sub = db.scalar(select(Subscription).where(Subscription.user_id == user.id))
    if sub:
        return sub
    now = datetime.now(timezone.utc)
    sub = Subscription(
        id=str(uuid.uuid4()),
        user_id=user.id,
        plan_id="free",
        status="active",
        created_at=now,
        updated_at=now,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub
