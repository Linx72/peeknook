# PeekNook — long-term plan

## v0.1 — Foundation ✅

- [x] Fork Open Notebook → `~/Projects/peeknook`
- [x] Rebrand UI (PeekNook)
- [x] Auto Ollama bootstrap
- [x] Tauri desktop shell

## v0.2 — Desktop stack ✅

- [x] Embedded SurrealDB, SQLite sync log, Vite UI, PyInstaller, Cloud MVP

## v1.0 — Desktop MVP ✅

- [x] Chat/sources, Tauri sidecar, macOS `.dmg`, signing script, GitHub Actions

## v1.5 — Cloud ✅

- [x] Auth, sync, MinIO blobs, web dashboard

## v2.0 — Auto sync ✅

- [x] Bi-directional sync, LWW conflicts, auto-sync loop, E2E flag

## v3.0 — Platform ✅

- [x] Teams, TermitPro API, billing (MVP)
- [x] Stripe webhook stub (`POST /billing/webhook/stripe`)
- [x] Production Docker Compose (`cloud/docker-compose.prod.yml`)

## v4.0 — Product polish ✅

- [x] Single UI parity — Vite: notes, vector search, home nav (Next.js legacy only)
- [x] Sync verify script (`scripts/peeknook-sync-verify.sh`)
- [x] Release build script (`scripts/peeknook-build-release.sh`) + CI optional signing
- [x] Stripe live checkout (when `STRIPE_SECRET_KEY` + price IDs set)
- [x] TermitPro IDE extension stub (`integrations/termitpro-vscode/`)

## v4.1 — Release hardening ✅

- [x] PDF sync verify script (Mac A→B simulation locally)
- [x] Notarization script + entitlements (`scripts/peeknook-notarize-macos.sh`)
- [x] Windows `.exe` / MSI smoke test in CI
- [x] Default dev workflow → Vite (`peeknook-dev.sh`; Next.js → `peeknook-dev-legacy.sh`)

## v4.2 — Ship ✅

- [x] PDF upload fix (`notebook_id` + `notebooks` form conflict)
- [x] Two-Mac PDF sync script (`scripts/peeknook-pdf-sync-two-mac.sh`)
- [x] Notarize step in release CI (when Apple secrets set)
- [x] Legacy Next.js moved to `legacy/frontend/` + parity audit script

## v4.3 — Complete UI + release ✅

- [x] Transformations + Podcasts pages in Vite UI
- [x] Two-Mac QA script (`scripts/peeknook-two-mac-qa.sh`)
- [x] GitHub Release publish on tag (`.dmg`, `.msi`, `.exe`)
- [x] Notarize CI step + secrets documented in README

## v4.4 — Single UI ship ✅

- [x] Model credentials + default models in Vite Settings
- [x] Transformation create/delete in Vite
- [x] Automated QA sign-off (`scripts/peeknook-qa-signoff.sh`)
- [x] Removed `legacy/frontend/` (Next.js)

## v5.0 — Profiles + i18n ✅

- [x] Podcast profile editor in Vite (`PodcastProfileEditor.tsx`)
- [x] i18n EN/RU (`ui/src/i18n/`) — nav, home, podcasts
- [x] Two-Mac PDF sync `auto` mode (`peeknook-pdf-sync-two-mac.sh auto`)
- [x] Field test wrapper (`scripts/peeknook-field-test.sh`)

## v5.1 — Full i18n + model discovery ✅

- [x] Full i18n EN/RU on all Vite pages (notebooks, search, settings, cloud, team, billing, transformations)
- [x] Discover/register models in Settings (`ModelCredentials` — discover, register all, sync provider/all)
- [x] Release tag script (`scripts/peeknook-release-tag.sh`)

## v5.2 — Podcast i18n + Windows sign ✅

- [x] PodcastProfileEditor + generate form i18n EN/RU
- [x] Windows code signing in CI (`peeknook-sign-windows.ps1`, optional secrets)
- [x] Physical two-Mac record script (`peeknook-two-mac-physical-record.sh`)

## v5.3 — Auto-update + release prep ✅

- [x] Tauri updater plugin (signed bundles, `latest.json` on GitHub Releases)
- [x] Settings → Check for updates (`AppUpdater.tsx`, EN/RU)
- [x] Version bump `0.2.0`, CI publishes updater artifacts + manifest
- [x] `./scripts/peeknook-push-release.sh` (tag + push)

## v5.4 — Ship automation ✅

- [x] Auto-detect GitHub repo for updater (`peeknook-github-repo.sh`)
- [x] Pre-ship checklist (`peeknook-ship-check.sh`)
- [x] CI uses resolved repo for updater endpoint

## v5.5 — Release (repo live, CI billing gate) ✅

- [x] GitHub repo [Linx72/peeknook](https://github.com/Linx72/peeknook) (public)
- [x] Tag `v0.2.0` pushed
- [x] Secrets: `TAURI_SIGNING_PRIVATE_KEY` + password
- [x] GitHub Release [v0.2.0](https://github.com/Linx72/peeknook/releases/tag/v0.2.0) — local build upload (DMG + updater)
- [ ] GitHub Actions release — **blocked: billing/spending limit** on Linx72 account (optional after billing fix)

## v5.6 — Local ship ✅

- [x] Local release fallback: `./scripts/peeknook-local-release.sh`
- [x] Publish helper: `./scripts/peeknook-publish-local-release.sh` (build + `gh release upload`)
- [x] Field test + QA sign-off (`peeknook-field-test.sh`)
- [x] Auto two-Mac simulation (`peeknook-pdf-sync-two-mac.sh auto`)
- [ ] Physical two-Mac on separate hardware → `peeknook-two-mac-physical-record.sh`

## v5.7 — Repo sync + public updater ✅

- [x] Sync script: `./scripts/peeknook-sync-github-repo.sh` (export + force-push when histories diverge)
- [x] `.gitignore` — exclude `cloud/peeknook_blobs/` and dev sqlite
- [x] Push sync to [Linx72/peeknook](https://github.com/Linx72/peeknook) main
- [x] **Public repo** — updater `latest.json` reachable without auth
- [ ] Apple code signing + notarization (when `APPLE_*` secrets available)
- [ ] Windows `.msi` build (CI after billing, or manual on Windows)

## v5.8 — Next

- [ ] GitHub Actions release (fix Linx72 billing/spending limit)
- [ ] Physical two-Mac on separate hardware → `peeknook-two-mac-physical-record.sh`
- [ ] Git LFS for `peeknook-api-aarch64-apple-darwin` binary (>50 MB warning)
