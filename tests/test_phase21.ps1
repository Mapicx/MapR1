# Phase 2.1 Test Script
Write-Host "`n=== MapR1 Phase 2.1 Test Suite ===" -ForegroundColor Cyan

$baseUrl = "http://localhost:8000"

# Test 1: Health Check
Write-Host "`n1. Testing Health..." -ForegroundColor Yellow
$health = Invoke-RestMethod -Uri "$baseUrl/health"
Write-Host "   ✓ Status: $($health.status)" -ForegroundColor Green

# Test 2: Create Project
Write-Host "`n2. Creating Project..." -ForegroundColor Yellow
$projectBody = @{
    name = "Test Project"
    description = "Phase 2.1 test"
} | ConvertTo-Json

$project = Invoke-RestMethod -Uri "$baseUrl/api/projects" `
    -Method Post -ContentType "application/json" -Body $projectBody

Write-Host "   ✓ Project: $($project.name)" -ForegroundColor Green
Write-Host "   ✓ ID: $($project.id)" -ForegroundColor Green
$projectId = $project.id

# Test 3: Generate Scenarios
Write-Host "`n3. Generating Scenarios - takes 2 minutes..." -ForegroundColor Yellow
$scenarioBody = @{
    prompt = "What if we achieve carbon neutrality by 2030?"
    num_scenarios = 2
} | ConvertTo-Json

$response = Invoke-RestMethod `
    -Uri "$baseUrl/api/scenarios/generate?project_id=$projectId" `
    -Method Post -ContentType "application/json" -Body $scenarioBody `
    -TimeoutSec 180

Write-Host "   ✓ Generated: $($response.scenarios.Count) scenarios" -ForegroundColor Green
$scenarioId = $response.scenarios[0].id

# Test 4: Get Scenario
Write-Host "`n4. Getting Scenario..." -ForegroundColor Yellow
$scenario = Invoke-RestMethod -Uri "$baseUrl/api/scenarios/$scenarioId"
Write-Host "   ✓ Title: $($scenario.title)" -ForegroundColor Green
Write-Host "   ✓ Events: $($scenario.timeline.Count)" -ForegroundColor Green
Write-Host "   ✓ Saved: $($scenario.saved)" -ForegroundColor Green

# Test 5: Mark as Saved
Write-Host "`n5. Marking as Saved..." -ForegroundColor Yellow
$saved = Invoke-RestMethod -Uri "$baseUrl/api/scenarios/$scenarioId/save" -Method Post
Write-Host "   ✓ Saved: $($saved.saved)" -ForegroundColor Green

# Test 6: Get Project Stats
Write-Host "`n6. Project Stats..." -ForegroundColor Yellow
$stats = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId"
Write-Host "   ✓ Total: $($stats.stats.total_scenarios)" -ForegroundColor Green
Write-Host "   ✓ Saved: $($stats.stats.saved_scenarios)" -ForegroundColor Green

Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "✓ Phase 2.1 Tests Complete!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "`nProject ID: $projectId" -ForegroundColor Gray
Write-Host "Check Supabase dashboard to see the data`n" -ForegroundColor Gray
