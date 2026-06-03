# ── Job Hunter: API Backend ───────────────────────────────────────────────────
# EJECUTAR ESTE SCRIPT ANTES DE USAR CLAUDE DESKTOP CON MCP
$host.UI.RawUI.WindowTitle = "Job Hunter API :8000"
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Job Hunter API  — http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "  Swagger UI      — http://127.0.0.1:8000/docs" -ForegroundColor DarkCyan
Write-Host "  REQUERIDO por MCP tools de Claude Desktop" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Set-Location "$PSScriptRoot\src"
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
