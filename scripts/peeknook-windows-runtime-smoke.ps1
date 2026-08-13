# Verify the frozen PeekNook sidecar on a real Windows host.
param(
  [string]$SidecarPath = ""
)

$ErrorActionPreference = "Stop"

function Get-FreeTcpPort {
  $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
  $listener.Start()
  try {
    return ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
  }
  finally {
    $listener.Stop()
  }
}

function Get-HttpStatus {
  param([string]$Uri, [hashtable]$Headers = @{})

  try {
    $response = Invoke-WebRequest -Uri $Uri -Headers $Headers -TimeoutSec 5 -UseBasicParsing
    return [int]$response.StatusCode
  }
  catch {
    if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
      return [int]$_.Exception.Response.StatusCode
    }
    return 0
  }
}

function Wait-ForHttpStatus {
  param(
    [string]$Uri,
    [int]$ExpectedStatus,
    [int]$TimeoutSeconds = 180
  )

  $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
  do {
    if ((Get-HttpStatus -Uri $Uri) -eq $ExpectedStatus) {
      return
    }
    Start-Sleep -Milliseconds 500
  } while ([DateTime]::UtcNow -lt $deadline)

  throw "Timed out waiting for HTTP $ExpectedStatus from $Uri"
}

if (-not $SidecarPath) {
  $candidate = Get-ChildItem -Path "desktop/src-tauri/binaries" -Filter "peeknook-api-*.exe" -File |
    Select-Object -First 1
  if (-not $candidate) {
    throw "Windows PeekNook sidecar not found under desktop/src-tauri/binaries"
  }
  $SidecarPath = $candidate.FullName
}

$SidecarPath = (Resolve-Path $SidecarPath).Path
$tempBase = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { $env:TEMP }
$qaRoot = Join-Path $tempBase ("peeknook-windows-runtime-" + [Guid]::NewGuid().ToString("N"))
$stdoutLog = Join-Path $qaRoot "sidecar.stdout.log"
$stderrLog = Join-Path $qaRoot "sidecar.stderr.log"
$apiPort = Get-FreeTcpPort
$surrealPort = Get-FreeTcpPort
while ($surrealPort -eq $apiPort) {
  $surrealPort = Get-FreeTcpPort
}
$token = [Guid]::NewGuid().ToString()
$process = $null
$succeeded = $false
$shutdownFailed = $false

$runtimeEnvironment = @{
  API_PORT = $apiPort.ToString()
  API_RELOAD = "false"
  CORS_ORIGINS = "tauri://localhost,http://tauri.localhost,https://tauri.localhost"
  OPEN_NOTEBOOK_ENCRYPTION_KEY = "peeknook-windows-runtime-smoke"
  OPEN_NOTEBOOK_PASSWORD = $token
  PEEKNOOK_AUTO_OLLAMA = "false"
  PEEKNOOK_AUTO_SYNC = "false"
  PEEKNOOK_BIN_DIR = (Join-Path $qaRoot "bin")
  PEEKNOOK_DATA_DIR = (Join-Path $qaRoot "data")
  PEEKNOOK_EMBEDDED_DB = "true"
  PEEKNOOK_STANDALONE = "true"
  PEEKNOOK_SURREAL_PORT = $surrealPort.ToString()
  PEEKNOOK_SYNC_DB = (Join-Path $qaRoot "sync.sqlite")
  SURREAL_URL = "ws://127.0.0.1:$surrealPort/rpc"
}
$previousEnvironment = @{}

New-Item -ItemType Directory -Path $qaRoot | Out-Null

try {
  foreach ($key in $runtimeEnvironment.Keys) {
    $previousEnvironment[$key] = [Environment]::GetEnvironmentVariable($key, "Process")
    [Environment]::SetEnvironmentVariable($key, $runtimeEnvironment[$key], "Process")
  }
  $previousEnvironment["PEEKNOOK_SKIP_WORKER"] = [Environment]::GetEnvironmentVariable("PEEKNOOK_SKIP_WORKER", "Process")
  [Environment]::SetEnvironmentVariable("PEEKNOOK_SKIP_WORKER", $null, "Process")

  Write-Host "Starting Windows sidecar: $SidecarPath"
  Write-Host "QA API port: $apiPort; SurrealDB port: $surrealPort"
  $process = Start-Process -FilePath $SidecarPath -PassThru -NoNewWindow `
    -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog

  $healthUrl = "http://127.0.0.1:$apiPort/health"
  Wait-ForHttpStatus -Uri $healthUrl -ExpectedStatus 200

  $protectedStatus = Get-HttpStatus -Uri "http://127.0.0.1:$apiPort/api/notebooks"
  if ($protectedStatus -ne 401) {
    throw "Protected API returned $protectedStatus without a desktop token; expected 401"
  }

  $allowedResponse = Invoke-WebRequest -Uri $healthUrl -Headers @{ Origin = "tauri://localhost" } `
    -TimeoutSec 5 -UseBasicParsing
  if ($allowedResponse.Headers["Access-Control-Allow-Origin"] -ne "tauri://localhost") {
    throw "Tauri origin was not allowed by the packaged API"
  }
  $blockedResponse = Invoke-WebRequest -Uri $healthUrl -Headers @{ Origin = "https://evil.example" } `
    -TimeoutSec 5 -UseBasicParsing
  if ($blockedResponse.Headers["Access-Control-Allow-Origin"]) {
    throw "Untrusted origin received an Access-Control-Allow-Origin header"
  }

  Wait-ForHttpStatus -Uri "http://127.0.0.1:$surrealPort/health" -ExpectedStatus 200
  $surrealBinary = Join-Path $qaRoot "bin/surreal.exe"
  if (-not (Test-Path $surrealBinary)) {
    throw "SurrealDB was not installed by the Windows sidecar"
  }
  $surrealHash = (Get-FileHash -Algorithm SHA256 $surrealBinary).Hash.ToLowerInvariant()
  $expectedHash = "e9990dddd6580bb2a45332cb8c65b11edf855d8e03303f31616d67fa4c50cc00"
  if ($surrealHash -ne $expectedHash) {
    throw "Installed SurrealDB SHA-256 mismatch: $surrealHash"
  }

  $workerDeadline = [DateTime]::UtcNow.AddSeconds(60)
  do {
    $workers = @(Get-CimInstance Win32_Process | Where-Object {
      $_.CommandLine -and $_.CommandLine.Contains("peeknook-api") -and $_.CommandLine.Contains("--worker")
    })
    if ($workers.Count -gt 0) { break }
    Start-Sleep -Milliseconds 500
  } while ([DateTime]::UtcNow -lt $workerDeadline)
  if ($workers.Count -eq 0) {
    throw "Packaged background worker did not start"
  }

  Write-Host "Windows sidecar runtime smoke passed"
  $succeeded = $true
}
finally {
  if ($process -and -not $process.HasExited) {
    & taskkill.exe /PID $process.Id /T /F | Out-Null
    $process.WaitForExit(15000)
  }

  foreach ($key in $previousEnvironment.Keys) {
    [Environment]::SetEnvironmentVariable($key, $previousEnvironment[$key], "Process")
  }

  Start-Sleep -Milliseconds 500
  $apiListeners = @(Get-NetTCPConnection -LocalPort $apiPort -State Listen -ErrorAction SilentlyContinue)
  $surrealListeners = @(Get-NetTCPConnection -LocalPort $surrealPort -State Listen -ErrorAction SilentlyContinue)
  if ($apiListeners.Count -gt 0 -or $surrealListeners.Count -gt 0) {
    $succeeded = $false
    $shutdownFailed = $true
  }

  if (-not $succeeded) {
    if (Test-Path $stdoutLog) {
      Write-Host "--- sidecar stdout ---"
      Get-Content $stdoutLog -Tail 200
    }
    if (Test-Path $stderrLog) {
      Write-Host "--- sidecar stderr ---"
      Get-Content $stderrLog -Tail 200
    }
  }

  if (Test-Path $qaRoot) {
    Remove-Item -Path $qaRoot -Recurse -Force
  }
  if ($shutdownFailed) {
    throw "Windows sidecar left API or SurrealDB listening after shutdown"
  }
}
