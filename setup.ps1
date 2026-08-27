# =============================================================================
#  VitroFit — Setup Script (Windows / PowerShell)
# -----------------------------------------------------------------------------
#  Installs all dependencies needed to run the Backend API and the Web frontend.
#  Run from the repository root:
#
#      powershell -ExecutionPolicy Bypass -File .\setup.ps1
#
#  What this does:
#    1. BackendAPI\VitroFit.API  -> dotnet restore   (restores NuGet packages)
#    2. VitroFit_web             -> npm install      (installs Node packages)
#
#  NOTE: The Flutter mobile app (vitrofit_mobile) is NOT covered here.
#  After dependencies are installed, follow README.md to configure
#  appsettings.json / .env and start each app.
# =============================================================================

$ErrorActionPreference = 'Stop'

$Root = $PSScriptRoot

Write-Host "=== VitroFit dependency installer ===" -ForegroundColor Cyan

# -----------------------------------------------------------------------------
# 1. Backend — restore NuGet packages
# -----------------------------------------------------------------------------
$backendDir = Join-Path $Root 'BackendAPI\VitroFit.API'

if (Test-Path (Join-Path $backendDir 'VitroFit.API.csproj')) {
    Write-Host "`n[1/2] Restoring backend packages (.NET)..." -ForegroundColor Green
    Push-Location $backendDir
    try {
        dotnet restore
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Backend restore FAILED." -ForegroundColor Red
            exit $LASTEXITCODE
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Host "`n[1/2] SKIPPED backend - VitroFit.API.csproj not found." -ForegroundColor Yellow
}

# -----------------------------------------------------------------------------
# 2. Web — install npm dependencies
# -----------------------------------------------------------------------------
$webDir = Join-Path $Root 'VitroFit_web'

if (Test-Path (Join-Path $webDir 'package.json')) {
    Write-Host "`n[2/2] Installing web dependencies (npm)..." -ForegroundColor Green
    Push-Location $webDir
    try {
        npm install
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Web npm install FAILED." -ForegroundColor Red
            exit $LASTEXITCODE
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Host "`n[2/2] SKIPPED web - package.json not found." -ForegroundColor Yellow
}

Write-Host "`n=== Setup complete. ===" -ForegroundColor Cyan
Write-Host "Next steps (see README.md):"
Write-Host "  1. Configure BackendAPI\VitroFit.API\appsettings.json (DB connection string)"
Write-Host "  2. Run backend:  dotnet run  (in BackendAPI\VitroFit.API) - migrations and the"
Write-Host "                       admin account are applied automatically on startup"
Write-Host "  3. Run web:      npm run dev (in VitroFit_web)"
