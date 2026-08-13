# Build an unsigned MSIX for Microsoft Store certification and signing.
[CmdletBinding()]
param(
  [ValidateSet("Qa", "PartnerCenter")]
  [string]$Mode = "Qa",
  [string]$IdentityName = "",
  [string]$Publisher = "",
  [string]$PublisherDisplayName = "",
  [switch]$ConfirmPartnerCenterIdentity,
  [string]$Version = "",
  [string]$ExecutablePath = "desktop/src-tauri/target/release/desktop.exe",
  [string]$SidecarPath = "",
  [string]$OutputDirectory = "dist/windows-store"
)

$ErrorActionPreference = "Stop"

function ConvertTo-XmlText {
  param([Parameter(Mandatory)][string]$Value)

  if ($Value.Contains("`r") -or $Value.Contains("`n")) {
    throw "MSIX identity values cannot contain line breaks"
  }
  return [System.Security.SecurityElement]::Escape($Value)
}

function Resolve-ProjectPath {
  param(
    [Parameter(Mandatory)][string]$Root,
    [Parameter(Mandatory)][string]$Path
  )

  $candidate = if ([IO.Path]::IsPathRooted($Path)) { $Path } else { Join-Path $Root $Path }
  return (Resolve-Path $candidate).Path
}

function Get-ProjectOutputPath {
  param(
    [Parameter(Mandatory)][string]$Root,
    [Parameter(Mandatory)][string]$Path
  )

  $candidate = if ([IO.Path]::IsPathRooted($Path)) { $Path } else { Join-Path $Root $Path }
  return [IO.Path]::GetFullPath($candidate)
}

function Resolve-MakeAppx {
  $command = Get-Command MakeAppx.exe -ErrorAction SilentlyContinue
  if ($command) {
    return $command.Source
  }

  $sdkRoot = Join-Path ${env:ProgramFiles(x86)} "Windows Kits/10/bin"
  if (Test-Path $sdkRoot) {
    $candidate = Get-ChildItem -Path $sdkRoot -Recurse -Filter MakeAppx.exe -File |
      Where-Object { $_.FullName -match '[\\/]x64[\\/]MakeAppx\.exe$' } |
      Sort-Object { $_.VersionInfo.FileVersionRaw } -Descending |
      Select-Object -First 1
    if ($candidate) {
      return $candidate.FullName
    }
  }

  throw "MakeAppx.exe was not found. Install the Windows 10/11 SDK on this Windows host."
}

function ConvertTo-MsixVersion {
  param([Parameter(Mandatory)][string]$Value)

  if ($Value -match '^(\d+)\.(\d+)\.(\d+)$') {
    $parts = @([int]$Matches[1], [int]$Matches[2], [int]$Matches[3], 0)
  }
  elseif ($Value -match '^(\d+)\.(\d+)\.(\d+)\.(\d+)$') {
    $parts = @([int]$Matches[1], [int]$Matches[2], [int]$Matches[3], [int]$Matches[4])
  }
  else {
    throw "MSIX version must use three or four numeric parts: $Value"
  }

  if ($parts | Where-Object { $_ -lt 0 -or $_ -gt 65535 }) {
    throw "Every MSIX version part must be between 0 and 65535: $Value"
  }
  return ($parts -join ".")
}

if (-not $IsWindows) {
  throw "MSIX packaging must run on Windows because it requires MakeAppx.exe from the Windows SDK"
}

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$configPath = Join-Path $repositoryRoot "desktop/src-tauri/tauri.conf.json"
$tauriConfig = Get-Content $configPath -Raw | ConvertFrom-Json
if (-not $Version) {
  $Version = [string]$tauriConfig.version
}
$msixVersion = ConvertTo-MsixVersion -Value $Version

if ($Mode -eq "Qa") {
  if ($IdentityName -or $Publisher -or $PublisherDisplayName -or $ConfirmPartnerCenterIdentity) {
    throw "QA mode uses fixed synthetic identity values; remove Partner Center parameters"
  }
  $IdentityName = "ai.peeknook.desktop.qa"
  $Publisher = "CN=PeekNook QA"
  $PublisherDisplayName = "PeekNook QA"
}
else {
  if (-not $ConfirmPartnerCenterIdentity) {
    throw "PartnerCenter mode requires -ConfirmPartnerCenterIdentity after copying exact identity values from Partner Center"
  }
  if (-not $IdentityName -or -not $Publisher -or -not $PublisherDisplayName) {
    throw "PartnerCenter mode requires IdentityName, Publisher, and PublisherDisplayName"
  }
}

if ($IdentityName -notmatch '^[A-Za-z0-9.-]{3,50}$') {
  throw "MSIX IdentityName must contain 3-50 letters, digits, periods, or hyphens"
}
if ($Publisher -notmatch '^CN=') {
  throw "MSIX Publisher must be the exact Partner Center distinguished name beginning with CN="
}

$resolvedExecutable = Resolve-ProjectPath -Root $repositoryRoot -Path $ExecutablePath
if (-not $SidecarPath) {
  $sidecarCandidates = @(
    (Join-Path $repositoryRoot "desktop/src-tauri/target/release/peeknook-api.exe"),
    (Join-Path $repositoryRoot "desktop/src-tauri/binaries/peeknook-api-x86_64-pc-windows-msvc.exe")
  )
  $SidecarPath = $sidecarCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
  if (-not $SidecarPath) {
    throw "Windows PeekNook sidecar was not found. Run scripts/build-backend.sh first."
  }
}
$resolvedSidecar = Resolve-ProjectPath -Root $repositoryRoot -Path $SidecarPath
$resolvedOutputDirectory = Get-ProjectOutputPath -Root $repositoryRoot -Path $OutputDirectory
New-Item -ItemType Directory -Path $resolvedOutputDirectory -Force | Out-Null

$tempBase = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { $env:TEMP }
$workingRoot = Join-Path $tempBase ("peeknook-msix-" + [Guid]::NewGuid().ToString("N"))
$layoutRoot = Join-Path $workingRoot "layout"
$verifyRoot = Join-Path $workingRoot "verify"
$assetsRoot = Join-Path $layoutRoot "Assets"
$packageLabel = if ($Mode -eq "Qa") { "PeekNook-$msixVersion-x64-QA-UNSIGNED" } else { "PeekNook-$msixVersion-x64" }
$packagePath = Join-Path $resolvedOutputDirectory "$packageLabel.msix"
$metadataPath = Join-Path $resolvedOutputDirectory "$packageLabel.metadata.json"

try {
  New-Item -ItemType Directory -Path $assetsRoot -Force | Out-Null
  Copy-Item $resolvedExecutable (Join-Path $layoutRoot "PeekNook.exe")
  Copy-Item $resolvedSidecar (Join-Path $layoutRoot "peeknook-api.exe")

  $iconRoot = Join-Path $repositoryRoot "desktop/src-tauri/icons"
  foreach ($icon in @("StoreLogo.png", "Square44x44Logo.png", "Square150x150Logo.png")) {
    Copy-Item (Join-Path $iconRoot $icon) (Join-Path $assetsRoot $icon)
  }

  $identityXml = ConvertTo-XmlText $IdentityName
  $publisherXml = ConvertTo-XmlText $Publisher
  $publisherDisplayXml = ConvertTo-XmlText $PublisherDisplayName
  $manifest = @"
<?xml version="1.0" encoding="utf-8"?>
<Package
  xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
  xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
  xmlns:uap10="http://schemas.microsoft.com/appx/manifest/uap/windows10/10"
  xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
  IgnorableNamespaces="uap uap10 rescap">
  <Identity Name="$identityXml" Publisher="$publisherXml" Version="$msixVersion" ProcessorArchitecture="x64" />
  <Properties>
    <DisplayName>PeekNook</DisplayName>
    <PublisherDisplayName>$publisherDisplayXml</PublisherDisplayName>
    <Description>Desktop-first AI research for your own sources.</Description>
    <Logo>Assets\StoreLogo.png</Logo>
  </Properties>
  <Resources>
    <Resource Language="en-us" />
    <Resource Language="ru-ru" />
  </Resources>
  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.19041.0" MaxVersionTested="10.0.26100.0" />
  </Dependencies>
  <Capabilities>
    <rescap:Capability Name="runFullTrust" />
  </Capabilities>
  <Applications>
    <Application Id="PeekNook" Executable="PeekNook.exe" uap10:RuntimeBehavior="packagedClassicApp" uap10:TrustLevel="mediumIL">
      <uap:VisualElements
        DisplayName="PeekNook"
        Description="Desktop-first AI research for your own sources."
        BackgroundColor="transparent"
        Square44x44Logo="Assets\Square44x44Logo.png"
        Square150x150Logo="Assets\Square150x150Logo.png" />
    </Application>
  </Applications>
</Package>
"@
  $manifestPath = Join-Path $layoutRoot "AppxManifest.xml"
  Set-Content -Path $manifestPath -Value $manifest -Encoding utf8NoBOM

  $makeAppx = Resolve-MakeAppx
  if (Test-Path $packagePath) {
    Remove-Item $packagePath -Force
  }
  & $makeAppx pack /d $layoutRoot /p $packagePath /o
  if ($LASTEXITCODE -ne 0 -or -not (Test-Path $packagePath)) {
    throw "MakeAppx failed to create the PeekNook MSIX package"
  }

  & $makeAppx unpack /p $packagePath /d $verifyRoot /o
  if ($LASTEXITCODE -ne 0) {
    throw "MakeAppx failed to unpack the generated MSIX for verification"
  }

  foreach ($fileName in @("PeekNook.exe", "peeknook-api.exe")) {
    $sourceHash = (Get-FileHash -Algorithm SHA256 (Join-Path $layoutRoot $fileName)).Hash
    $packageHash = (Get-FileHash -Algorithm SHA256 (Join-Path $verifyRoot $fileName)).Hash
    if ($sourceHash -ne $packageHash) {
      throw "MSIX payload hash mismatch for $fileName"
    }
  }
  if (Test-Path (Join-Path $verifyRoot "AppxSignature.p7x")) {
    throw "The Store input package must remain unsigned; Microsoft signs it after certification"
  }

  [xml]$verifiedManifest = Get-Content (Join-Path $verifyRoot "AppxManifest.xml") -Raw
  $namespace = [System.Xml.XmlNamespaceManager]::new($verifiedManifest.NameTable)
  $namespace.AddNamespace("f", "http://schemas.microsoft.com/appx/manifest/foundation/windows10")
  $verifiedIdentity = $verifiedManifest.SelectSingleNode("/f:Package/f:Identity", $namespace)
  if (
    $verifiedIdentity.GetAttribute("Name") -ne $IdentityName -or
    $verifiedIdentity.GetAttribute("Publisher") -ne $Publisher -or
    $verifiedIdentity.GetAttribute("Version") -ne $msixVersion
  ) {
    throw "Generated MSIX identity does not match the requested values"
  }

  $metadata = [ordered]@{
    schema = "peeknook.windows-store-msix.v1"
    mode = $Mode
    package = [IO.Path]::GetFileName($packagePath)
    sha256 = (Get-FileHash -Algorithm SHA256 $packagePath).Hash.ToLowerInvariant()
    identityName = $IdentityName
    publisher = $Publisher
    publisherDisplayName = $PublisherDisplayName
    version = $msixVersion
    architecture = "x64"
    signed = $false
    directDistributionAllowed = $false
    partnerCenterIdentityConfirmed = ($Mode -eq "PartnerCenter")
    purpose = if ($Mode -eq "Qa") { "structure-only QA; do not submit or distribute" } else { "Microsoft Store submission candidate; do not sideload" }
  }
  Set-Content -Path $metadataPath -Value ($metadata | ConvertTo-Json -Depth 4) -Encoding utf8NoBOM

  Write-Host "MSIX package: $packagePath"
  Write-Host "Metadata: $metadataPath"
  if ($Mode -eq "Qa") {
    Write-Host "QA ONLY: synthetic identity; this package cannot be submitted or distributed."
  }
  else {
    Write-Host "STORE CANDIDATE ONLY: upload to Partner Center for certification and Microsoft signing; do not sideload."
  }
}
finally {
  if (Test-Path $workingRoot) {
    Remove-Item -Path $workingRoot -Recurse -Force
  }
}
