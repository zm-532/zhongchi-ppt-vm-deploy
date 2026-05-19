param([switch]$NoKill)

$rootDir = $PSScriptRoot
$backendDir = "$rootDir\backend"
$frontendDir = "$rootDir\frontend"

function Free-Port($port) {
  $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
  if ($connections) {
    $pids = $connections | ForEach-Object { $_.OwningProcess } | Sort-Object -Unique
    foreach ($p in $pids) {
      if ($p -gt 0) {
        $name = (Get-Process -Id $p -ErrorAction SilentlyContinue).ProcessName
        Write-Host "  Killing process $name (PID: $p) on port $port" -ForegroundColor Yellow
        try { Stop-Process -Id $p -Force -ErrorAction Stop } catch {}
      }
    }
    Start-Sleep 1
  }
}

Write-Host "=== Stopping services ===" -ForegroundColor Magenta
if (-not $NoKill) {
  Free-Port 3000
  Free-Port 8010
} else {
  Write-Host "  Skipped (NoKill flag)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== Starting Backend (port 8010) ===" -ForegroundColor Green
Start-Process -FilePath "uv" -ArgumentList "run","uvicorn","app.main:app","--host","127.0.0.1","--port","8010","--reload","--env-file","..\.env" -WorkingDirectory "$backendDir\src" -NoNewWindow -PassThru

Write-Host "=== Starting Frontend (port 3000) ===" -ForegroundColor Green
$env:NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8010"
Start-Process -FilePath "npm.cmd" -ArgumentList "run","dev" -WorkingDirectory $frontendDir -NoNewWindow -PassThru

Write-Host ""
Write-Host "=== Services started ===" -ForegroundColor Cyan
Write-Host "  Backend: http://127.0.0.1:8010" -ForegroundColor White
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop all services" -ForegroundColor Yellow

Start-Sleep 2