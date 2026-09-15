$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not (Test-Path '.venv\Scripts\python.exe')) { python -m venv .venv }
$python = Join-Path $root '.venv\Scripts\python.exe'
& $python -m pip install -q -r requirements.txt
Remove-Item -LiteralPath 'dist\package' -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path 'dist\package' | Out-Null
& $python -m pip install -q -r requirements.txt --target dist\package
Copy-Item app,worker -Destination dist\package -Recurse
Write-Host 'Lambda package staging directory is ready.'
