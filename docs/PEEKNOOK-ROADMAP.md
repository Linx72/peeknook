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
- [x] GitHub Actions release — macOS DMG + Windows `.exe`/`.msi` via [CI run](https://github.com/Linx72/peeknook/actions/runs/28159385341)

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
- [x] Windows `.msi` + `.exe` via GitHub Actions CI

## v5.8 — CI fixes + sidecar hygiene

- [x] Exclude sidecar binary from git (CI/local `build-backend.sh` builds it)
- [x] Fix Windows updater config path (`RUNNER_TEMP` not `/tmp`)
- [x] Notarize step skips when `APPLE_*` unset (no longer blocks artifact upload)
- [x] Publish job runs on tag ref for `workflow_dispatch` too
- [x] Re-run PeekNook Release CI — macOS + Windows + publish ✅
- [ ] Physical two-Mac on separate hardware → `peeknook-two-mac-physical-record.sh`
- [ ] Apple notarization (when `APPLE_*` secrets set in repo)

## v5.9 — Ship verify ✅

- [x] Release verify script (`peeknook-verify-release.sh`) — manifest + all assets HTTP 200
- [x] Ship complete wrapper (`peeknook-ship-complete.sh`) — automated gates + manual checklist
- [x] v0.2.0 verified: macOS DMG, Windows exe/msi, updater sigs, `latest.json`

## v6.0 — Ship-ready ✅ (manual gates only)

- [x] Product shippable at **v0.2.0** — CI release, public updater, all automated QA green
- [x] Local CI mirror: `./scripts/peeknook-ci-local.sh`
- [x] Sidecar bootstrap: `./scripts/peeknook-ensure-sidecar.sh`
- [x] Re-run release CI: `./scripts/peeknook-retry-release-ci.sh v0.2.0`
- [ ] **Physical two-Mac** — real hardware A→B; handoff file after `push` → `~/Library/Application Support/PeekNook/two-mac-handoff.json`
- [ ] **Apple notarization** — `./scripts/peeknook-apple-secrets-hints.sh`, then `./scripts/peeknook-retry-release-ci.sh v0.2.0`
- [ ] **v0.2.1+** — tag when product changes ship

## v6.1 — Post-ship polish ✅

- [x] Settings → download links (macOS DMG, Windows exe/msi) EN/RU
- [x] Two-Mac handoff JSON after machine A push
- [x] Cloud prod verify: `./scripts/peeknook-cloud-prod-verify.sh`
- [x] Apple secrets helper: `./scripts/peeknook-apple-secrets-hints.sh`

## v6.2 — Cloud + downloads ✅

- [x] Dynamic release URLs from GitHub `latest.json` (Settings downloads)
- [x] Home → «Download desktop app» CTA
- [x] Cloud prod up: `./scripts/peeknook-cloud-prod-up.sh`
- [x] Stripe verify: `./scripts/peeknook-stripe-verify.sh`
- [x] `.env.prod` gitignored

## v6.3 — Manual ship gates

- [ ] Physical two-Mac (handoff JSON on machine A)
- [ ] Apple notarization (`peeknook-apple-secrets-hints.sh` → retry CI)
- [ ] Cloud prod deploy on your VPS (`peeknook-cloud-prod-up.sh` + DNS)
- [ ] Stripe live keys in prod `.env.prod`

## v6.4 — Two-Mac UX + ops ✅

- [x] API `GET /peeknook/two-mac-handoff` — reads machine-A handoff JSON
- [x] Cloud Sync UI — handoff banner + prefill cloud URL/email
- [x] Settings — E2E sync toggle (dev)
- [x] `./scripts/peeknook-health-all.sh` — API + cloud + Ollama + release
- [x] `./scripts/peeknook-cloud-deploy-pack.sh` — VPS deploy tarball

## v6.5 — Manual (unchanged)

- [ ] Physical two-Mac on real hardware → `./scripts/peeknook-two-mac-machine-b.sh --record`
- [ ] Apple notarization + retry CI
- [ ] VPS: deploy pack + `cloud/deploy/nginx.peeknook.conf.example` + TLS
- [ ] Stripe live in `.env.prod`

## v6.6 — Two-Mac automation + VPS templates ✅

- [x] `./scripts/peeknook-two-mac-machine-b.sh` — read handoff, pull, optional `--record`
- [x] Cloud Sync — «Login & pull from handoff» button
- [x] Settings — auto-sync interval + sync conflicts panel
- [x] `./scripts/peeknook-stripe-webhook-test.sh` — dev webhook stub
- [x] `cloud/deploy/nginx.peeknook.conf.example` — TLS reverse proxy

## v6.7 — Full stack dev + release prep ✅

- [x] `./scripts/peeknook-cloud-dev.sh` — local cloud with billing routes
- [x] `./scripts/peeknook-dev-full.sh` — cloud + API + Vite UI
- [x] `./scripts/peeknook-bump-version.sh` — sync semver Tauri/UI/cloud
- [x] `./scripts/peeknook-cloud-certbot-hints.sh` — TLS on VPS
- [x] Nav sync pending badge + Home cloud status
- [x] Cloud Sync — copy handoff JSON to clipboard

## v6.8 — v0.2.1 ship ✅

- [x] Bump **0.2.1** (`peeknook-bump-version.sh`) — Tauri, UI, cloud, releaseAssets
- [x] `./scripts/peeknook-ship-release.sh 0.2.1` — ship-check + sync + tag + CI
- [x] Fix sync overlay — `SyncConflictsPanel.tsx` + auto-overlay `ui/src` / `cloud/api`
- [x] GitHub Release CI green: [run](https://github.com/Linx72/peeknook/actions/runs/28172460928)
- [x] `peeknook-verify-release.sh` — v0.2.1 DMG, exe, msi, updater ✅
- [ ] Physical two-Mac `--record` on real hardware
- [ ] VPS deploy + certbot + Stripe live
- [ ] Apple notarization

## v6.9 — Sync hygiene ✅

- [x] Auto-overlay uncommitted `ui/src`, `cloud/api`, `cloud/deploy`, `api/routers` in sync script
- [x] `peeknook-ship-complete.sh` — dynamic retry tag from `tauri.conf.json`
- [x] v0.2.1 release verified on GitHub

## v7.0 — Manual ship gates (unchanged)

- [ ] Physical two-Mac — Mac A: `peeknook-pdf-sync-two-mac.sh push` → Mac B: `peeknook-two-mac-machine-b.sh --record`
- [ ] Apple notarization — `peeknook-apple-secrets-hints.sh` → retry CI
- [ ] VPS — `peeknook-cloud-deploy-pack.sh` + `peeknook-cloud-certbot-hints.sh`
- [ ] Stripe live — keys in `cloud/.env.prod`, verify with `peeknook-stripe-verify.sh`

## v7.1 — Next product ✅

- [x] In-app release notes (Settings → what's new from GitHub release body)
- [x] Cloud prod health on Home — `GET /peeknook/cloud-health` + health link
- [x] Optional `PEEKNOOK_SHIP_LOCAL=1` in `peeknook-ship-release.sh` (local DMG + gh upload)

## v7.2 — v0.2.2 ship ✅

- [x] Bump **0.2.2** — release notes + cloud health UI
- [x] `./scripts/peeknook-ship-release.sh 0.2.2` — sync + tag + CI
- [x] GitHub Release CI green: [run](https://github.com/Linx72/peeknook/actions/runs/28176162542)
- [x] `peeknook-verify-release.sh` — v0.2.2 DMG, exe, msi, updater ✅
- [x] VPS deploy pack generated (`peeknook-cloud-deploy-pack.sh`)
- [ ] Physical two-Mac `--record` on real hardware
- [ ] VPS deploy + certbot + Stripe live
- [ ] Apple notarization

## v7.3 — Manual gates only

- [ ] Physical two-Mac — Mac A: `peeknook-pdf-sync-two-mac.sh push` → Mac B: `peeknook-two-mac-machine-b.sh --record`
- [ ] Apple notarization — `peeknook-apple-secrets-hints.sh` → retry CI
- [ ] VPS — unpack deploy pack + `peeknook-cloud-certbot-hints.sh`
- [ ] Stripe live — `cloud/.env.prod` + `peeknook-stripe-verify.sh`

## v7.4 — Ship checklist + gates wizard ✅

- [x] `GET /peeknook/ship-status` — physical two-Mac, cloud health, handoff
- [x] Settings → Ship checklist panel (`ShipChecklist.tsx`)
- [x] Billing → Stripe live/dev indicator (`GET /billing/config`)
- [x] `./scripts/peeknook-manual-gates.sh` — all automatable prep in one command
- [x] `peeknook-apple-secrets-hints.sh` — dynamic version tag

## v7.5 — v0.2.3 ship ✅

- [x] Bump **0.2.3** — ship checklist + billing stripe badge
- [x] `./scripts/peeknook-ship-release.sh 0.2.3`
- [x] GitHub Release CI: [run](https://github.com/Linx72/peeknook/actions/runs/28177864757)
- [x] `peeknook-verify-release.sh` after CI
- [x] `./scripts/peeknook-manual-gates.sh` — prep wizard

## v7.6 — Manual only

- [ ] Physical two-Mac `--record` on real hardware
- [ ] Apple notarization + retry CI
- [ ] VPS deploy + TLS
- [ ] Stripe live in `cloud/.env.prod`

## v7.7 — VPS deploy + ship status ✅

- [x] `./scripts/peeknook-vps-deploy.sh` — scp pack + docker compose on VPS (when `PEEKNOOK_VPS_SSH` set)
- [x] Ship status — Stripe live + HTTPS VPS detection + deploy pack flag
- [x] Ship checklist — refresh, copy manual-gates command

## v7.8 — v0.2.4 ship

- [ ] Bump **0.2.4** — VPS deploy script + ship status v2
- [ ] `./scripts/peeknook-ship-release.sh 0.2.4`
- [ ] Verify release after CI
