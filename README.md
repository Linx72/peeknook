# PeekNook

**Peek into your sources. Ask anything.**

Desktop-first AI research for **Windows** and **macOS**, with optional **PeekNook Cloud** sync.

Desktop runtime and local API security: [Russian operator note](docs/PEEKNOOK-DESKTOP-RUNTIME-RU.md).

Canonical source: the private **RepoBase / Forgejo** repository at `timeweb/peeknook`. The separate public repository at `releases/peeknook-releases` contains only the distribution contract and must never receive source code or secrets. Its `main` branch and `v*` tags are protected. Anonymous UI, API, and raw-file access are enabled; a real signed release asset has not been published yet. Local branch `main` tracks protected `repobase/main`, and the published history excludes the local-only `cloud/peeknook_cloud_dev.sqlite` database. Run `scripts/peeknook-repobase-preflight.sh` before any source push. GitHub is treated only as an explicitly enabled legacy bridge for native CI/public updater assets during migration. See [the Russian migration note](docs/PEEKNOOK-REPOBASE-MIGRATION-RU.md).

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

Порты выше — значения для разработки. Установленное desktop-приложение выбирает свободные локальные порты API и SurrealDB при каждом запуске.

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

**Native release bridge** (tag `v*`): temporary GitHub-hosted macOS/Windows runners build the native packages, but the workflow publishes the verified release to RepoBase first. Only after that succeeds does it publish a GitHub bridge release for already-installed legacy clients. Tag publication fails closed unless updater signing, macOS Developer ID signing/notarization, Windows Authenticode verification, and the scoped RepoBase release token are all available. A manual workflow run on a branch may still create unsigned QA artifacts, but it cannot publish a release.

If the temporary native release bridge is unavailable, build locally:

```bash
./scripts/peeknook-local-release.sh              # build + copy to ~/Library/Application Support/PeekNook/releases/
./scripts/peeknook-publish-local-release.sh v0.2.0 # legacy GitHub upload; requires explicit bridge opt-in
```

The local release path also requires a signed and notarized app. For an explicitly non-publishable QA build only, set `PEEKNOOK_ALLOW_UNSIGNED_LOCAL_RELEASE=1`.

Current legacy public release: [v0.2.7](https://github.com/Linx72/peeknook/releases/latest). The next RepoBase distribution endpoint is contractually defined as `https://repobase.ru/releases/peeknook-releases/releases/latest/download/latest.json`, but installed clients still use the guarded legacy bridge. Anonymous access to the public repository is verified. The endpoint intentionally remains inactive because no real signed RepoBase release asset exists yet; a signed bridge release through the legacy channel is also still required. Validate the future channel with `python scripts/peeknook-release-channel.py --json`. Runtime gates remain available through `./scripts/peeknook-gates-status.sh`.

The old GitHub sync path is mutation-guarded after choosing RepoBase:

```bash
PEEKNOOK_ALLOW_GITHUB_LEGACY_RELEASE=1 ./scripts/peeknook-sync-github-repo.sh
```

Do not use that bridge as the canonical source. Remote `repobase` is configured as `git@repobase.ru:timeweb/peeknook.git`; verify the boundary with `scripts/peeknook-repobase-preflight.sh` before any push.

Required repo secrets for public macOS builds:

| Secret | Purpose |
|--------|---------|
| `APPLE_CERTIFICATE` | Base64-encoded Developer ID Application `.p12` |
| `APPLE_CERTIFICATE_PASSWORD` | Password of the exported `.p12` |
| `KEYCHAIN_PASSWORD` | Temporary CI keychain password |
| `APPLE_ID` | Apple ID email |
| `APPLE_PASSWORD` | App-specific password |
| `APPLE_TEAM_ID` | Team ID |

The CI imports the certificate and discovers `APPLE_SIGNING_IDENTITY` automatically. For a local build, install the certificate in Keychain and export `APPLE_SIGNING_IDENTITY` before `tauri build`. See the [Tauri macOS signing guide](https://v2.tauri.app/distribute/sign/macos/).

Required repo secrets for public Windows builds:

| Secret | Purpose |
|--------|---------|
| `WINDOWS_CERTIFICATE` | Base64-encoded `.pfx` code-signing cert |
| `WINDOWS_CERTIFICATE_PASSWORD` | PFX password |
| `WINDOWS_SIGNING_TIMESTAMP_URL` | Timestamp server (optional) |

RepoBase publication additionally requires `REPOBASE_RELEASE_TOKEN`. It is
configured from the restricted `peeknook-release-bot` account, which belongs only
to the `Publishers` team for `releases/peeknook-releases`. The token has only the
`write:repository` scope and is passed to GitHub Secrets through standard input;
do not replace it with an administrator token or expose it in command arguments.

The certificate is imported before `tauri build`, so Authenticode is applied before the Tauri updater signature is calculated. See the [Tauri Windows signing guide](https://v2.tauri.app/distribute/sign/windows/).

There is also a separate **Microsoft Store MSIX** path that does not require a
project-owned Windows certificate: Microsoft signs an accepted MSIX after Store
certification. It does not make the direct-download EXE/MSI publishable and it
does not use the Tauri updater. The manual `PeekNook Windows Store MSIX QA`
workflow currently creates only a synthetic-identity, non-publishable structural
artifact. A submission candidate can be created only after reserving the app in
Partner Center and copying its exact Identity and Publisher values. See the
[Russian operator guide](docs/PEEKNOOK-WINDOWS-STORE-RU.md).

Tauri updater signing (required for in-app updates):

| Secret | Purpose |
|--------|---------|
| `TAURI_SIGNING_PRIVATE_KEY` | Contents of `.tauri/peeknook.key` (generate via `tauri signer generate`) |
| `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | Private key password |

Set `PEEKNOOK_GITHUB_REPO=owner/repo` when building if releases live on a fork.

```bash
# Local release tag (runs field test + creates annotated tag)
./scripts/peeknook-release-tag.sh v0.2.0
./scripts/peeknook-push-release.sh v0.2.0   # tag + push to RepoBase remote
```

```bash
# Local signed + notarized build (macOS certificate already in Keychain)
export APPLE_SIGNING_IDENTITY="Developer ID Application: …"
export APPLE_ID=… APPLE_PASSWORD=… APPLE_TEAM_ID=…
bash scripts/peeknook-build-release.sh
bash scripts/peeknook-verify-macos-release.sh
```

Подробное объяснение границ публичного релиза: [`docs/PEEKNOOK-RELEASE-INTEGRITY-RU.md`](docs/PEEKNOOK-RELEASE-INTEGRITY-RU.md).

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
