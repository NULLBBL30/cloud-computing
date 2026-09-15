param([switch]$KeepRunning)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path '.venv\Scripts\python.exe')) { python -m venv .venv }
$python = Join-Path $root '.venv\Scripts\python.exe'
& $python -m pip install -q -r requirements.txt

$env:AWS_ACCESS_KEY_ID = 'testing'; $env:AWS_SECRET_ACCESS_KEY = 'testing'; $env:AWS_REGION = 'us-east-1'
$env:MOTO_ENDPOINT = 'http://127.0.0.1:5000'; $env:TENANT_KEYS = '{"demo-key-a":"retailer-a","demo-key-b":"retailer-b"}'
New-Item -ItemType Directory -Force -Path 'data\raw\runtime' | Out-Null

$moto = Start-Process -FilePath $python -ArgumentList '-m','moto.server','-H','127.0.0.1','-p','5000' -RedirectStandardOutput 'data\raw\runtime\moto.log' -RedirectStandardError 'data\raw\runtime\moto.err.log' -PassThru
try {
  Start-Sleep -Seconds 2
  & $python -c 'from app.aws import bootstrap_resources; bootstrap_resources()'
  $api = Start-Process -FilePath $python -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000' -RedirectStandardOutput 'data\raw\runtime\api.log' -RedirectStandardError 'data\raw\runtime\api.err.log' -PassThru
  $worker = Start-Process -FilePath $python -ArgumentList '-m','worker.worker' -RedirectStandardOutput 'data\raw\runtime\worker.log' -RedirectStandardError 'data\raw\runtime\worker.err.log' -PassThru
  Start-Sleep -Seconds 2
  Invoke-RestMethod http://127.0.0.1:8000/health | Out-Host
  & $python -m pytest -q
  Write-Host 'Ready: API http://127.0.0.1:8000/docs'
  if ($KeepRunning) { Wait-Process -Id $api.Id }
} finally {
  if (-not $KeepRunning) { $api,$worker,$moto | Where-Object { $_ } | Stop-Process -Force -ErrorAction SilentlyContinue }
}
