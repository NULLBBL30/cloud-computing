$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path '.venv\Scripts\python.exe')) { python -m venv .venv }
$python = Join-Path $root '.venv\Scripts\python.exe'
& $python -m pip install -q -r requirements.txt
& $python -m pytest -q

if ($LASTEXITCODE -ne 0) { throw 'Validation failed.' }
Write-Host 'Validation passed. Push main to trigger the Alibaba Cloud deployment workflow.'
