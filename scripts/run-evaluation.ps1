param(
  [Parameter(Mandatory = $true)] [string] $BaseUrl,
  [switch] $Quick
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path '.venv\Scripts\python.exe')) { python -m venv .venv }
$python = Join-Path $root '.venv\Scripts\python.exe'
& $python -m pip install -q -r requirements.txt

$base = $BaseUrl.TrimEnd('/')
$runId = Get-Date -Format 'yyyyMMdd-HHmmss'
$minutes = if ($Quick) { 1 } else { 5 }
$profiles = @(
  @{ Name = 'idle'; Users = 1; Minutes = $minutes },
  @{ Name = 'low'; Users = 10; Minutes = $minutes },
  @{ Name = 'target'; Users = 50; Minutes = if ($Quick) { 1 } else { 10 } },
  @{ Name = 'high'; Users = 100; Minutes = if ($Quick) { 1 } else { 10 } },
  @{ Name = 'stress'; Users = 150; Minutes = if ($Quick) { 1 } else { 10 } }
)

foreach ($profile in $profiles) {
  $output = Join-Path $root "data\raw\load\$runId-$($profile.Name)"
  New-Item -ItemType Directory -Force -Path $output | Out-Null
  @{
    run_id = $runId
    profile = $profile.Name
    users = $profile.Users
    duration_minutes = $profile.Minutes
    base_url = $base
    region = 'cn-hangzhou'
    timestamp_utc = (Get-Date).ToUniversalTime().ToString('o')
    commit = (git rev-parse HEAD)
  } | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $output 'run-metadata.json')
  & $python -m locust -f load\locustfile.py --headless --host $base --users $profile.Users --spawn-rate ([Math]::Max(1, [Math]::Ceiling($profile.Users / 10))) --run-time "$($profile.Minutes)m" --csv (Join-Path $output 'locust') --csv-full-history
  if ($LASTEXITCODE -ne 0) { throw "Locust failed for $($profile.Name)" }
}

& $python analysis\analyse_results.py
Write-Host "Evaluation complete. Raw files are in data\raw\load\$runId and summary is in data\derived\load-summary.csv."
