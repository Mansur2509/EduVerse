$ErrorActionPreference = "Stop"

$backendRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $backendRoot ".venv\Scripts\python.exe"
$dependencyPath = Join-Path $backendRoot ".deps"
$databasePath = Join-Path $backendRoot "uniway_local.sqlite3"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Missing backend virtual environment: $pythonPath"
}

if (-not (Test-Path -LiteralPath $dependencyPath)) {
    throw "Missing local backend dependencies: $dependencyPath"
}

$env:PYTHONPATH = $dependencyPath
$env:DATABASE_URL = "sqlite:///$($databasePath.Replace('\', '/'))"
$env:DJANGO_DEBUG = "true"
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1"
$env:CORS_ALLOWED_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
$env:CSRF_TRUSTED_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"

Push-Location $backendRoot
try {
    & $pythonPath manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) {
        throw "Django migrations failed."
    }

    & $pythonPath manage.py seed_demo --with-demo-data
    if ($LASTEXITCODE -ne 0) {
        throw "Demo seed failed."
    }

    Write-Host ""
    Write-Host "UniWay backend is ready at http://127.0.0.1:8000" -ForegroundColor Green
    Write-Host "Keep this window open while previewing the beta."
    & $pythonPath manage.py runserver 127.0.0.1:8000
}
finally {
    Pop-Location
}
