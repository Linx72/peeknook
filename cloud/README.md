# PeekNook Cloud (v1.5 MVP)

Auth, API keys, and sync stub for PeekNook Desktop.

## Local (SQLite, no Docker)

```bash
cd cloud
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8090
```

Open http://localhost:8090/docs

## Docker (Postgres + MinIO)

```bash
cd cloud
docker compose up -d
```

## Quick test

```bash
curl -X POST http://localhost:8090/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"secret123"}'
```
