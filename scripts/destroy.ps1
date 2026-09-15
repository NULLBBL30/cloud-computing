Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*cloud computing*\.venv*' } | Stop-Process -Force
Write-Host 'Stopped local platform processes. Raw experiment data was preserved.'
