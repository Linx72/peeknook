"""PeekNook Cloud database session."""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL", "sqlite+pysqlite:///./peeknook_cloud_dev.sqlite"
)

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    import api.models  # noqa: F401 — register models with Base

    Base.metadata.create_all(bind=engine)
    _migrate_schema()


def _migrate_schema() -> None:
    """Add columns introduced after first deploy (SQLite dev DB)."""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    tables = set(insp.get_table_names())
    alters: list[str] = []
    if "sync_events" in tables:
        cols = {c["name"] for c in insp.get_columns("sync_events")}
        if "team_id" not in cols:
            alters.append("ALTER TABLE sync_events ADD COLUMN team_id VARCHAR(36)")
    if "blobs" in tables:
        cols = {c["name"] for c in insp.get_columns("blobs")}
        if "team_id" not in cols:
            alters.append("ALTER TABLE blobs ADD COLUMN team_id VARCHAR(36)")
    if not alters:
        return
    with engine.begin() as conn:
        for sql in alters:
            conn.execute(text(sql))
