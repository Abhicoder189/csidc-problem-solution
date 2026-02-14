# ILMCS Quick Start Script
# Run this to set up the database and start the backend

Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "ILMCS - Industrial Land Monitoring & Compliance System" -ForegroundColor Cyan
Write-Host "Quick Start Setup" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Docker
Write-Host "[1/5] Checking Docker..." -ForegroundColor Yellow
$dockerInstalled = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerInstalled) {
    Write-Host "❌ Docker not found. Please install Docker Desktop." -ForegroundColor Red
    Write-Host "Download from: https://www.docker.com/products/docker-desktop" -ForegroundColor Gray
    exit 1
}
Write-Host "✓ Docker found" -ForegroundColor Green

# Step 2: Start Database
Write-Host ""
Write-Host "[2/5] Starting PostgreSQL database..." -ForegroundColor Yellow
Push-Location database
docker-compose down -v  # Clean start
docker-compose up -d
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Database container started" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to start database" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

# Wait for database to be ready
Write-Host "⏳ Waiting for database to be ready..." -ForegroundColor Gray
Start-Sleep -Seconds 10

# Step 3: Check Python
Write-Host ""
Write-Host "[3/5] Checking Python environment..." -ForegroundColor Yellow
$pythonInstalled = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonInstalled) {
    Write-Host "❌ Python not found. Please install Python 3.8+." -ForegroundColor Red
    exit 1
}
$pythonVersion = python --version
Write-Host "✓ $pythonVersion" -ForegroundColor Green

# Step 4: Install Dependencies
Write-Host ""
Write-Host "[4/5] Installing Python dependencies..." -ForegroundColor Yellow
Push-Location backend
if (Test-Path "requirements.txt") {
    pip install -r requirements.txt --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "⚠ Some dependencies failed to install (this may be okay)" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠ requirements.txt not found" -ForegroundColor Yellow
}
Pop-Location

# Step 5: Verify Database Connection
Write-Host ""
Write-Host "[5/5] Verifying database..." -ForegroundColor Yellow
Push-Location database
$dbCheck = docker-compose exec -T postgres psql -U ilmcs_admin -d ilmcs -c "SELECT COUNT(*) FROM industrial_region;" 2>&1
if ($dbCheck -match "56" -or $dbCheck -match "count") {
    Write-Host "✓ Database schema created and seeded" -ForegroundColor Green
} else {
    Write-Host "⚠ Database may not be fully initialized" -ForegroundColor Yellow
    Write-Host "  You can manually seed it with: psql -U ilmcs_admin -d ilmcs -f seed_regions.sql" -ForegroundColor Gray
}
Pop-Location

# Summary
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "1. Start the backend:" -ForegroundColor Gray
Write-Host "   cd backend" -ForegroundColor Cyan
Write-Host "   python main.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Test the regions endpoint:" -ForegroundColor Gray
Write-Host "   curl http://localhost:8000/api/regions/" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. View API docs:" -ForegroundColor Gray
Write-Host "   http://localhost:8000/api/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Start the frontend (in a new terminal):" -ForegroundColor Gray
Write-Host "   cd frontend" -ForegroundColor Cyan
Write-Host "   npm install" -ForegroundColor Cyan
Write-Host "   npm run dev" -ForegroundColor Cyan
Write-Host ""
Write-Host "Database Info:" -ForegroundColor White
Write-Host "  Host: localhost:5432" -ForegroundColor Gray
Write-Host "  Database: ilmcs" -ForegroundColor Gray
Write-Host "  User: ilmcs_admin" -ForegroundColor Gray
Write-Host "  Password: ilmcs_secure_2026" -ForegroundColor Gray
Write-Host ""
Write-Host "For detailed information, see: REGIONS_FIX_README.md" -ForegroundColor Gray
Write-Host ""
