# Quick Test Script for MapR1 Phase 1
# Tests all endpoints and displays results

Write-Host "`n=== MapR1 Phase 1 Quick Test ===" -ForegroundColor Cyan
Write-Host "Testing API endpoints...`n" -ForegroundColor Cyan

# Test 1: Health Check
Write-Host "1. Testing Health Endpoint..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
    Write-Host "   ✓ Status: $($health.status)" -ForegroundColor Green
    Write-Host "   ✓ App: $($health.app)`n" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Health check failed. Is the server running?" -ForegroundColor Red
    Write-Host "   Run: python main.py`n" -ForegroundColor Yellow
    exit 1
}

# Test 2: LLM Health Check
Write-Host "2. Testing LLM Health..." -ForegroundColor Yellow
try {
    $llmHealth = Invoke-RestMethod -Uri "http://localhost:8000/api/scenarios/health" -Method Get
    Write-Host "   ✓ Ollama: $($llmHealth.ollama)" -ForegroundColor Green
    Write-Host "   ✓ Model: $($llmHealth.model)" -ForegroundColor Green
    Write-Host "   ✓ Status: $($llmHealth.status)`n" -ForegroundColor Green
} catch {
    Write-Host "   ✗ LLM health check failed" -ForegroundColor Red
    Write-Host "   Make sure Ollama is running: ollama serve`n" -ForegroundColor Yellow
    exit 1
}

# Test 3: Scenario Generation
Write-Host "3. Testing Scenario Generation..." -ForegroundColor Yellow
Write-Host "   Prompt: 'What if renewable energy becomes free by 2028?'" -ForegroundColor Gray
Write-Host "   (This will take 1-2 minutes...)`n" -ForegroundColor Gray

$body = @{
    prompt = "What if renewable energy becomes free by 2028?"
    num_scenarios = 2
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/scenarios/generate" `
        -Method Post `
        -ContentType "application/json" `
        -Body $body `
        -TimeoutSec 180
    
    Write-Host "   ✓ Generated $($response.scenarios.Count) scenarios`n" -ForegroundColor Green
    
    # Display scenarios
    foreach ($scenario in $response.scenarios) {
        Write-Host "   ━━━ $($scenario.title) ━━━" -ForegroundColor Cyan
        Write-Host "   Category: $($scenario.category)" -ForegroundColor White
        Write-Host "   Probability: $($scenario.probability)" -ForegroundColor White
        Write-Host "   Description: $($scenario.description)`n" -ForegroundColor Gray
        
        Write-Host "   Timeline:" -ForegroundColor White
        foreach ($event in $scenario.timeline) {
            Write-Host "     • $($event.year): $($event.description)" -ForegroundColor Gray
            Write-Host "       Impact: $($event.impact)" -ForegroundColor DarkGray
        }
        Write-Host ""
    }
    
    Write-Host "`n=== All Tests Passed! ===" -ForegroundColor Green
    Write-Host "Phase 1 is working correctly.`n" -ForegroundColor Green
    
} catch {
    Write-Host "   ✗ Scenario generation failed" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)`n" -ForegroundColor Red
    exit 1
}
