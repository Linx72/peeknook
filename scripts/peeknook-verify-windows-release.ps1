# Verify Authenticode and Tauri updater signatures for Windows installers.
param(
  [string]$BundleRoot = "desktop/src-tauri/target/release/bundle"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BundleRoot)) {
  throw "Bundle root not found: $BundleRoot"
}

$installers = @(Get-ChildItem -Path $BundleRoot -Recurse -File -ErrorAction SilentlyContinue | Where-Object {
  $_.Extension -in @(".exe", ".msi")
})
if ($installers.Count -eq 0) {
  throw "No Windows installers found under: $BundleRoot"
}

foreach ($installer in $installers) {
  $signature = Get-AuthenticodeSignature -FilePath $installer.FullName
  if ($signature.Status -ne [System.Management.Automation.SignatureStatus]::Valid) {
    throw "Invalid Authenticode signature for $($installer.FullName): $($signature.Status)"
  }
  if (-not $signature.SignerCertificate) {
    throw "Missing signer certificate for: $($installer.FullName)"
  }
  Write-Host "Authenticode valid: $($installer.Name)"
}

$updaterInstallers = @(Get-ChildItem -Path $BundleRoot -Recurse -File -Filter "*setup*.exe" -ErrorAction SilentlyContinue)
if ($updaterInstallers.Count -eq 0) {
  throw "No NSIS updater installer found under: $BundleRoot"
}
foreach ($installer in $updaterInstallers) {
  $updaterSignature = "$($installer.FullName).sig"
  if (-not (Test-Path $updaterSignature) -or (Get-Item $updaterSignature).Length -eq 0) {
    throw "Missing or empty Tauri updater signature: $updaterSignature"
  }
  Write-Host "Tauri updater signature present: $([IO.Path]::GetFileName($updaterSignature))"
}

Write-Host "Windows release signature checks passed"
