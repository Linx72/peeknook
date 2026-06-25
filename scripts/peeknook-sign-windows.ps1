# Code-sign PeekNook Windows installers (.exe / .msi).
#
# Env (CI secrets):
#   WINDOWS_CERTIFICATE          Base64-encoded .pfx
#   WINDOWS_CERTIFICATE_PASSWORD PFX password
#   WINDOWS_SIGNING_TIMESTAMP_URL  Optional (default: DigiCert)
#
# Usage:
#   pwsh scripts/peeknook-sign-windows.ps1
#   pwsh scripts/peeknook-sign-windows.ps1 -BundleRoot desktop/src-tauri/target/release/bundle
param(
  [string]$BundleRoot = "desktop/src-tauri/target/release/bundle"
)

$ErrorActionPreference = "Stop"

if (-not $env:WINDOWS_CERTIFICATE) {
  Write-Host "Set WINDOWS_CERTIFICATE (base64 PFX) to sign. Unsigned artifacts remain at: $BundleRoot"
  exit 0
}

if (-not (Test-Path $BundleRoot)) {
  Write-Error "Bundle root not found: $BundleRoot — run: cd desktop; npm run tauri build"
}

$signtool = Get-ChildItem -Path "${env:ProgramFiles(x86)}\Windows Kits\10\bin" -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
  Sort-Object FullName -Descending |
  Select-Object -First 1

if (-not $signtool) {
  Write-Error "signtool.exe not found. Install Windows SDK on the runner."
}

$pfxPath = Join-Path $env:RUNNER_TEMP "peeknook-sign.pfx"
if (-not $env:RUNNER_TEMP) { $pfxPath = Join-Path $env:TEMP "peeknook-sign.pfx" }
[IO.File]::WriteAllBytes($pfxPath, [Convert]::FromBase64String($env:WINDOWS_CERTIFICATE))

$timestamp = $env:WINDOWS_SIGNING_TIMESTAMP_URL
if (-not $timestamp) { $timestamp = "http://timestamp.digicert.com" }

$files = Get-ChildItem -Path $BundleRoot -Recurse -Include *.exe, *.msi -ErrorAction SilentlyContinue
if (-not $files) {
  Write-Error "No .exe or .msi files under $BundleRoot"
}

Write-Host "Signing $($files.Count) file(s) with $($signtool.FullName)"
foreach ($file in $files) {
  Write-Host "  $($file.FullName)"
  & $signtool.FullName sign /fd SHA256 /f $pfxPath /p $env:WINDOWS_CERTIFICATE_PASSWORD /tr $timestamp /td SHA256 $file.FullName
  if ($LASTEXITCODE -ne 0) {
    Write-Error "signtool failed for $($file.FullName)"
  }
}

Remove-Item -Force $pfxPath -ErrorAction SilentlyContinue
Write-Host "Done — signed Windows artifacts under $BundleRoot"
