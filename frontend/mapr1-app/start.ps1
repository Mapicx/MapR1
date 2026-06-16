# MapR1 Frontend Start Script
# This script starts the frontend development server

Write-Host "🚀 Starting MapR1 Frontend..." -ForegroundColor Green
Write-Host ""

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
    npm install
    Write-Host ""
}

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "⚙️  Creating .env file..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✅ Created .env file" -ForegroundColor Green
    Write-Host ""
}

# Display backend connection info
Write-Host "🔗 Backend Configuration:" -ForegroundColor Cyan
Write-Host "   API URL: http://localhost:8000/api" -ForegroundColor Gray
Write-Host "   Make sure your backend is running!" -ForegroundColor Yellow
Write-Host ""

# Start the dev server
Write-Host "🌐 Starting development server..." -ForegroundColor Green
Write-Host "   Frontend will be available at: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""

npm run dev
