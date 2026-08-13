# Import a code-signing certificate before Tauri creates Windows installers.
param(
  [switch]$Cleanup
)

$ErrorActionPreference = "Stop"

if ($Cleanup) {
  $thumbprints = @($env:PEEKNOOK_IMPORTED_WINDOWS_CERTIFICATES -split "," | Where-Object { $_ })
  foreach ($thumbprint in $thumbprints) {
    if ($thumbprint -notmatch "^[A-Fa-f0-9]{40,64}$") {
      throw "Refusing to remove a certificate with an invalid thumbprint: $thumbprint"
    }
    $certificatePath = "Cert:\CurrentUser\My\$thumbprint"
    if (Test-Path $certificatePath) {
      Remove-Item -Path $certificatePath -Force
    }
  }
  Write-Host "Removed $($thumbprints.Count) imported Windows certificate(s)"
  exit 0
}

foreach ($variable in @("WINDOWS_CERTIFICATE", "WINDOWS_CERTIFICATE_PASSWORD", "GITHUB_ENV")) {
  if (-not [Environment]::GetEnvironmentVariable($variable, "Process")) {
    throw "Missing required environment variable: $variable"
  }
}

$tempBase = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { $env:TEMP }
$pfxPath = Join-Path $tempBase ("peeknook-windows-signing-" + [Guid]::NewGuid().ToString("N") + ".pfx")
$importedThumbprints = @()

try {
  try {
    $certificateBytes = [Convert]::FromBase64String($env:WINDOWS_CERTIFICATE)
  }
  catch {
    throw "WINDOWS_CERTIFICATE is not valid base64"
  }
  if ($certificateBytes.Length -eq 0) {
    throw "WINDOWS_CERTIFICATE decoded to an empty file"
  }
  [IO.File]::WriteAllBytes($pfxPath, $certificateBytes)

  $password = ConvertTo-SecureString -String $env:WINDOWS_CERTIFICATE_PASSWORD -Force -AsPlainText
  $imported = @(Import-PfxCertificate -FilePath $pfxPath -CertStoreLocation Cert:\CurrentUser\My -Password $password)
  $importedThumbprints = @($imported | ForEach-Object { $_.Thumbprint })
  $codeSigningCertificates = @($imported | Where-Object {
    $certificate = $_
    $codeSigningUsage = @($certificate.EnhancedKeyUsageList | Where-Object {
      $_.ObjectId.Value -eq "1.3.6.1.5.5.7.3.3"
    })
    $certificate.HasPrivateKey -and $codeSigningUsage.Count -gt 0
  } | Sort-Object NotAfter -Descending)

  if ($codeSigningCertificates.Count -eq 0) {
    throw "The PFX does not contain a code-signing certificate with a private key"
  }
  $signingCertificate = $codeSigningCertificates[0]
  $now = [DateTime]::UtcNow
  if ($signingCertificate.NotBefore.ToUniversalTime() -gt $now -or $signingCertificate.NotAfter.ToUniversalTime() -le $now) {
    throw "The Windows code-signing certificate is not currently valid"
  }

  $allThumbprints = $importedThumbprints -join ","
  Add-Content -Path $env:GITHUB_ENV -Value "WINDOWS_CERTIFICATE_THUMBPRINT=$($signingCertificate.Thumbprint)"
  Add-Content -Path $env:GITHUB_ENV -Value "PEEKNOOK_IMPORTED_WINDOWS_CERTIFICATES=$allThumbprints"
  Write-Host "Imported Windows code-signing certificate: $($signingCertificate.Subject)"
}
catch {
  foreach ($thumbprint in $importedThumbprints) {
    Remove-Item -Path "Cert:\CurrentUser\My\$thumbprint" -Force -ErrorAction SilentlyContinue
  }
  throw
}
finally {
  Remove-Item -Path $pfxPath -Force -ErrorAction SilentlyContinue
}
