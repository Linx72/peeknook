# PeekNook

**Peek into your sources. Ask anything.**

Desktop-first AI research for **Windows** and **macOS**, with optional **PeekNook Cloud** sync.

Based on [Open Notebook](https://github.com/lfnovo/open-notebook) (MIT). See [NOTICE.md](NOTICE.md).

## Architecture (v0.2)

```
PeekNook Desktop (Tauri)
  └── ui/          Vite + React shell (:5173)
  └── backend/     Python FastAPI (:5056)
  └── surreal      Embedded RocksDB (no Docker)
  └── sync.sqlite  Event log for cloud sync

PeekNook Cloud (:8090)
  └── auth, API keys, sync, blobs
  └── teams, billing (Free/Pro/Team)
  └── TermitPro API `/termitpro/v1/*`
  └── Postgres + MinIO (docker compose)
```

## Quick start

One command (embedded DB + API + Vite UI):

```bash
cd ~/Projects/peeknook
cp .env.example .env   # set OPEN_NOTEBOOK_ENCRYPTION_KEY
./scripts/peeknook-dev.sh
```

Open **http://localhost:5173** — API docs at **http://localhost:5056/docs**

With **PeekNook Cloud** locally (sync, billing, teams):

```bash
./scripts/peeknook-dev-full.sh   # cloud :8090 + API + Vite UI
# or cloud only:
./scripts/peeknook-cloud-dev.sh
```

### Manual steps

#### 1. Backend only

```bash
export PEEKNOOK_EMBEDDED_DB=true
export API_PORT=5056
./scripts/peeknook-backend.sh
```

Data: `~/Library/Application Support/PeekNook/`

#### 2. Vite UI only

```bash
cd ui && npm install && npm run dev
```

#### 3. Desktop app (Tauri)

```bash
cd desktop && npm install && npm run tauri dev
```

#### 4. TermitPro IDE integration

```bash
cd integrations/termitpro-vscode && npm install && npm run compile
```

In VS Code / TermitPro: **PeekNook: Show Status**, **Search Knowledge**, **Open Notebooks UI**.

Configure `peeknook.apiUrl` (default `http://127.0.0.1:5056`).

#### 5. PeekNook Cloud

```bash
cd cloud && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8090
```

Or: `cd cloud && docker compose up -d`

Docs: **http://localhost:8090/docs**

#### 6. Build release (.dmg / sidecar)

```bash
./scripts/peeknook-build-release.sh
```

**GitHub Release** (tag `v*`): CI builds macOS `.dmg` + Windows `.exe`/`.msi`, signs/notarizes when secrets set, publishes to Releases.

If GitHub Actions billing is unavailable, build and publish locally:

```bash
./scripts/peeknook-local-release.sh              # build + copy to ~/Library/Application Support/PeekNook/releases/
./scripts/peeknook-publish-local-release.sh v0.2.0 # upload to GitHub Releases (requires gh auth)
```

Current release: [v0.2.1](https://github.com/Linx72/peeknook/releases/latest) (ship: `./scripts/peeknook-ship-release.sh 0.2.1`). In-app auto-update fetches `latest.json` from GitHub Releases.

If local `main` diverged from GitHub export:

```bash
./scripts/peeknook-sync-github-repo.sh                    # dry-run
PEEKNOOK_SYNC_PUSH=1 ./scripts/peeknook-sync-github-repo.sh  # force-push clean tree
```

Required repo secrets for notarized macOS builds:

| Secret | Purpose |
|--------|---------|
| `APPLE_SIGNING_IDENTITY` | Developer ID Application cert name |
| `APPLE_ID` | Apple ID email |
| `APPLE_PASSWORD` | App-specific password |
| `APPLE_TEAM_ID` | Team ID |

Windows signing (optional):

| Secret | Purpose |
|--------|---------|
| `WINDOWS_CERTIFICATE` | Base64-encoded `.pfx` code-signing cert |
| `WINDOWS_CERTIFICATE_PASSWORD` | PFX password |
| `WINDOWS_SIGNING_TIMESTAMP_URL` | Timestamp server (optional) |

Tauri updater signing (required for in-app updates):

| Secret | Purpose |
|--------|---------|
| `TAURI_SIGNING_PRIVATE_KEY` | Contents of `.tauri/peeknook.key` (generate via `tauri signer generate`) |
| `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | Private key password |

Set `PEEKNOOK_GITHUB_REPO=owner/repo` when building if releases live on a fork.

```bash
# Local release tag (runs field test + creates annotated tag)
./scripts/peeknook-release-tag.sh v0.2.0
./scripts/peeknook-push-release.sh v0.2.0   # tag + push to GitHub
```

```bash
# Local sign + notarize (macOS)
export APPLE_SIGNING_IDENTITY="Developer ID Application: …"
export APPLE_ID=… APPLE_PASSWORD=… APPLE_TEAM_ID=…
bash scripts/peeknook-sign-macos.sh
```

#### 7. Verify sync & QA

```bash
./scripts/peeknook-sync-verify.sh
./scripts/peeknook-pdf-sync-verify.sh
./scripts/peeknook-two-mac-qa.sh
./scripts/peeknook-qa-signoff.sh       # records automated sign-off
./scripts/peeknook-pdf-sync-two-mac.sh auto   # one-machine push+pull
# After physical test on two Macs:
# export PEEKNOOK_SYNC_SOURCE_ID=source:… && ./scripts/peeknook-two-mac-physical-record.sh
./scripts/peeknook-ship-check.sh          # pre-release: build + field test
./scripts/peeknook-verify-release.sh      # GitHub Release + latest.json
./scripts/peeknook-ship-complete.sh       # all automated gates + manual checklist
./scripts/peeknook-ci-local.sh            # mirror GitHub PeekNook CI locally
./scripts/peeknook-ensure-sidecar.sh      # build sidecar after fresh clone
```

### Build backend binary (PyInstaller)

```bash
./scripts/build-backend.sh
```

Output: `dist/peeknook-backend/`

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `PEEKNOOK_EMBEDDED_DB` | `true` | Embedded SurrealDB vs Docker |
| `PEEKNOOK_SURREAL_PORT` | `8001` | Local DB port |
| `API_PORT` | `5056` | PeekNook API |
| `PEEKNOOK_AUTO_OLLAMA` | `true` | Auto-configure Ollama |
| `OPEN_NOTEBOOK_ENCRYPTION_KEY` | — | Required |

## Roadmap

[docs/PEEKNOOK-ROADMAP.md](docs/PEEKNOOK-ROADMAP.md)

## License

MIT
