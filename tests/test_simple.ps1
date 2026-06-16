# Simple Phase 2.1 Test Script
# Run each test step by step with clear output

Write-Host ""
Write-Host "=== MapR1 Phase 2.1 Simple Test ===" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "http://localhost:8000"

# Test 1: Health Check
Write-Host "1. Testing Health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$baseUrl/health"
    Write-Host "   Status: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "   ERROR: $_" -ForegroundColor Red
    exit 1
}

# Test 2: Create Project
Write-Host ""
Write-Host "2. Creating Project..." -ForegroundColor Yellow
try {
    $projectBody = @{
        name = "Test Project"
        description = "Phase 2.1 test"
    } | ConvertTo-Json

    $project = Invoke-RestMethod -Uri "$baseUrl/api/projects" -Method Post -ContentType "application/json" -Body $projectBody
    $projectId = $project.id
    Write-Host "   Project: $($project.name)" -ForegroundColor Green
    Write-Host "   ID: $projectId" -ForegroundColor Green
} catch {
    Write-Host "   ERROR: $_" -ForegroundColor Red
    exit 1
}

# Test 3: Generate Scenarios
Write-Host ""
Write-Host "3. Generating Scenarios (this takes 1-2 minutes)..." -ForegroundColor Yellow
try {
    $scenarioBody = @{
        prompt = "What if we achieve carbon neutrality by 2030?"
        num_scenarios = 2
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "$baseUrl/api/scenarios/generate?project_id=$projectId" -Method Post -ContentType "application/json" -Body $scenarioBody -TimeoutSec 180
    $scenarioId = $response.scenarios[0].id
    Write-Host "   Generated: $($response.scenarios.Count) scenarios" -ForegroundColor Green
    Write-Host "   First scenario ID: $scenarioId" -ForegroundColor Green
} catch {
    Write-Host "   ERROR: $_" -ForegroundColor Red
    exit 1
}

# Test 4: Get Scenario
Write-Host ""
Write-Host "4. Getting Scenario Details..." -ForegroundColor Yellow
try {
    $scenario = Invoke-RestMethod -Uri "$baseUrl/api/scenarios/$scenarioId"
    Write-Host "   Title: $($scenario.title)" -ForegroundColor Green
    Write-Host "   Timeline events: $($scenario.timeline.Count)" -ForegroundColor Green
    Write-Host "   Saved: $($scenario.saved)" -ForegroundColor Green
} catch {
    Write-Host "   ERROR: $_" -ForegroundColor Red
    exit 1
}

# Test 5: Mark as Saved
Write-Host ""
Write-Host "5. Marking Scenario as Saved..." -ForegroundColor Yellow
try {
    $saved = Invoke-RestMethod -Uri "$baseUrl/api/scenarios/$scenarioId/save" -Method Post
    Write-Host "   Saved: $($saved.saved)" -ForegroundColor Green
} catch {
    Write-Host "   ERROR: $_" -ForegroundColor Red
    exit 1
}

# Test 6: Get Project Stats
Write-Host ""
Write-Host "6. Getting Project Stats..." -ForegroundColor Yellow
try {
    $stats = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId"
    Write-Host "   Total scenarios: $($stats.stats.total_scenarios)" -ForegroundColor Green
    Write-Host "   Saved scenarios: $($stats.stats.saved_scenarios)" -ForegroundColor Green
} catch {
    Write-Host "   ERROR: $_" -ForegroundColor Red
    exit 1
}

# Success
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "All Tests Passed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project ID: $projectId" -ForegroundColor Gray
Write-Host "Scenario ID: $scenarioId" -ForegroundColor Gray
Write-Host ""
Write-Host "Check Supabase dashboard to verify data persistence:" -ForegroundColor Gray
Write-Host "https://ygtzasxbpizkupixmgcg.supabase.co" -ForegroundColor Gray
Write-Host ""
