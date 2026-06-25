"""PeekNook Cloud API — accounts, sync, teams, billing, TermitPro bridge."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.billing import check_storage_limit, check_sync_limit, router as billing_router
from api.database import get_db, init_db
from api.deps import create_token, ensure_subscription, get_current_user, hash_password, verify_password
from api.models import ApiKey, BlobRecord, SyncEvent, User
from api.teams import router as teams_router
from api.termitpro import router as termitpro_router

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="PeekNook Cloud API", version="0.2.3")
app.include_router(billing_router)
app.include_router(teams_router)
app.include_router(termitpro_router)


class SyncEventIn(BaseModel):
    id: str
    object_type: str
    object_id: str
    operation: str
    payload: Optional[str] = None
    created_at: str


class SyncPushBody(BaseModel):
    events: list[SyncEventIn] = Field(default_factory=list)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    created_at: datetime


class ApiKeyCreated(ApiKeyResponse):
    api_key: str


@app.on_event("startup")
def startup() -> None:
    init_db()
    from api import storage as blob_storage

    blob_storage.LOCAL_BLOB_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/", response_class=HTMLResponse)
def dashboard():
    index = WEB_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>PeekNook Cloud</h1><p><a href='/docs'>API docs</a></p>")


@app.get("/health")
def health():
    return {"status": "healthy", "service": "peeknook-cloud", "version": "0.2.3"}


@app.post("/auth/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(400, "Email already registered")
    user = User(
        id=str(uuid.uuid4()),
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    ensure_subscription(user, db)
    return TokenResponse(access_token=create_token(user.id))


@app.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    return TokenResponse(access_token=create_token(user.id))


@app.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "created_at": user.created_at}


@app.post("/api-keys", response_model=ApiKeyCreated)
def create_api_key(
    body: ApiKeyCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    raw = f"pk_{secrets.token_urlsafe(32)}"
    prefix = raw[:10]
    record = ApiKey(
        id=str(uuid.uuid4()),
        user_id=user.id,
        name=body.name,
        key_hash=hashlib.sha256(raw.encode()).hexdigest(),
        key_prefix=prefix,
        created_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()
    return ApiKeyCreated(
        id=record.id,
        name=record.name,
        key_prefix=record.key_prefix,
        created_at=record.created_at,
        api_key=raw,
    )


@app.get("/api-keys", response_model=list[ApiKeyResponse])
def list_api_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    keys = db.scalars(select(ApiKey).where(ApiKey.user_id == user.id)).all()
    return [
        ApiKeyResponse(
            id=k.id, name=k.name, key_prefix=k.key_prefix, created_at=k.created_at
        )
        for k in keys
    ]


@app.post("/sync/push")
def sync_push(
    body: SyncPushBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_sync_limit(user, db, new_events=len(body.events))
    stored = skipped = 0
    for event in body.events:
        exists = db.scalar(
            select(SyncEvent).where(
                SyncEvent.user_id == user.id,
                SyncEvent.client_event_id == event.id,
            )
        )
        if exists:
            skipped += 1
            continue
        created = datetime.fromisoformat(event.created_at.replace("Z", "+00:00"))
        db.add(
            SyncEvent(
                id=str(uuid.uuid4()),
                user_id=user.id,
                client_event_id=event.id,
                object_type=event.object_type,
                object_id=event.object_id,
                operation=event.operation,
                payload_json=event.payload,
                created_at=created,
            )
        )
        stored += 1
    db.commit()
    return {"accepted": True, "stored": stored, "skipped": skipped, "user_id": user.id}


@app.get("/sync/pull")
def sync_pull(
    since: Optional[str] = None,
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(SyncEvent).where(SyncEvent.user_id == user.id).order_by(SyncEvent.created_at.asc())
    if since:
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        query = query.where(SyncEvent.created_at > since_dt)
    rows = db.scalars(query.limit(limit)).all()
    return {
        "events": [
            {
                "id": row.id,
                "object_type": row.object_type,
                "object_id": row.object_id,
                "operation": row.operation,
                "payload_json": row.payload_json,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]
    }


@app.post("/blobs/upload")
async def upload_blob(
    object_type: str = Form(...),
    object_id: str = Form(...),
    filename: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from api import storage as blob_storage

    data = await file.read()
    check_storage_limit(user, db, extra_bytes=len(data))
    blob_id = str(uuid.uuid4())
    storage_key, digest = blob_storage.upload_blob(
        user.id, blob_id, data, file.content_type or "application/octet-stream"
    )
    db.add(
        BlobRecord(
            id=blob_id,
            user_id=user.id,
            object_type=object_type,
            object_id=object_id,
            filename=filename,
            storage_key=storage_key,
            size_bytes=len(data),
            content_type=file.content_type or "application/octet-stream",
            sha256=digest,
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    return {
        "id": blob_id,
        "object_type": object_type,
        "object_id": object_id,
        "filename": filename,
        "size_bytes": len(data),
        "sha256": digest,
        "backend": blob_storage.storage_backend(),
    }


@app.get("/blobs")
def list_blobs(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 100,
    object_id: Optional[str] = None,
):
    query = select(BlobRecord).where(BlobRecord.user_id == user.id)
    if object_id:
        query = query.where(BlobRecord.object_id == object_id)
    rows = db.scalars(query.order_by(BlobRecord.created_at.desc()).limit(limit)).all()
    total_bytes = db.scalar(
        select(func.coalesce(func.sum(BlobRecord.size_bytes), 0)).where(BlobRecord.user_id == user.id)
    )
    return {
        "total_bytes": total_bytes or 0,
        "items": [
            {
                "id": r.id,
                "object_type": r.object_type,
                "object_id": r.object_id,
                "filename": r.filename,
                "size_bytes": r.size_bytes,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


@app.get("/blobs/{blob_id}")
def download_blob(
    blob_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from api import storage as blob_storage

    record = db.get(BlobRecord, blob_id)
    if not record or record.user_id != user.id:
        raise HTTPException(404, "Blob not found")
    data, _ = blob_storage.download_blob(record.storage_key)
    return Response(
        content=data,
        media_type=record.content_type,
        headers={"Content-Disposition": f'attachment; filename="{record.filename}"'},
    )


@app.get("/dashboard/stats")
def dashboard_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from api.models import TeamMember

    events = db.scalar(select(func.count()).select_from(SyncEvent).where(SyncEvent.user_id == user.id))
    blobs = db.scalar(select(func.count()).select_from(BlobRecord).where(BlobRecord.user_id == user.id))
    bytes_used = db.scalar(
        select(func.coalesce(func.sum(BlobRecord.size_bytes), 0)).where(BlobRecord.user_id == user.id)
    )
    keys = db.scalar(select(func.count()).select_from(ApiKey).where(ApiKey.user_id == user.id))
    teams = db.scalar(select(func.count()).select_from(TeamMember).where(TeamMember.user_id == user.id))
    sub = ensure_subscription(user, db)
    return {
        "sync_events": events or 0,
        "blobs": blobs or 0,
        "storage_bytes": bytes_used or 0,
        "api_keys": keys or 0,
        "teams": teams or 0,
        "plan_id": sub.plan_id,
    }
