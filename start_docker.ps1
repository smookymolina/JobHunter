# Job Hunter: Docker startup
# Mata cualquier proceso local en puerto 8000 antes de Docker

$ErrorActionPreference = "SilentlyContinue"

$proc = Get-NetTCPConnection -LocalPort 8000 -State Listen | Select-Object -First 1
if ($proc) {
    $pid8000 = (Get-Process -Id $proc.OwningProcess).Id
    Write-Host "Puerto 8000 ocupado (PID $pid8000) - cerrando proceso local..." -ForegroundColor Yellow
    Stop-Process -Id $pid8000 -Force
    Start-Sleep -Seconds 1
} else {
    Write-Host "Puerto 8000 libre." -ForegroundColor Green
}

$ErrorActionPreference = "Stop"

Write-Host "Levantando Docker..." -ForegroundColor Cyan
docker compose up --build
