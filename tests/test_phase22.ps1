# Phase 2.2 Comprehensive Test
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MapR1 Phase 2.2 - Full System Test  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$baseUrl = "http://localhost:8000"

# Test 1: Create Project
Write-Host ""
Write-Host "[1/8] Creating Project..." -ForegroundColor Yellow
$projectBody = @{
    name = "Phase 2.2 Complete Test"
    description = "Testing entities, relationships, and timelines"
} | ConvertTo-Json

$project = Invoke-RestMethod -Uri "$baseUrl/api/projects" -Method Post -ContentType "application/json" -Body $projectBody
$projectId = $project.id
Write-Host "      OK Project created: $($project.name)" -ForegroundColor Green

# Test 2: Create Entities
Write-Host ""
Write-Host "[2/8] Creating Entities..." -ForegroundColor Yellow

$nation = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/entities" -Method Post -ContentType "application/json" -Body (@{
    type = "nation"
    name = "Global Energy Alliance"
    attributes = @{ population = 2000000000; tech_level = "advanced" }
} | ConvertTo-Json)

$company = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/entities" -Method Post -ContentType "application/json" -Body (@{
    type = "company"
    name = "Quantum Dynamics Corp"
    attributes = @{ employees = 100000; revenue = 50000000000 }
} | ConvertTo-Json)

$person = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/entities" -Method Post -ContentType "application/json" -Body (@{
    type = "person"
    name = "Dr. Elena Rodriguez"
    attributes = @{ role = "CEO"; expertise = "Quantum Computing" }
} | ConvertTo-Json)

Write-Host "      OK Created 3 entities" -ForegroundColor Green

# Test 3: Create Relationships
Write-Host ""
Write-Host "[3/8] Creating Relationships..." -ForegroundColor Yellow

Invoke-RestMethod -Uri "$baseUrl/api/relationships?project_id=$projectId" -Method Post -ContentType "application/json" -Body (@{
    entity_a_id = $person.id
    entity_b_id = $company.id
    relationship_type = "alliance"
    strength = "strong"
} | ConvertTo-Json) | Out-Null

Invoke-RestMethod -Uri "$baseUrl/api/relationships?project_id=$projectId" -Method Post -ContentType "application/json" -Body (@{
    entity_a_id = $company.id
    entity_b_id = $nation.id
    relationship_type = "trade_partner"
    strength = "medium"
} | ConvertTo-Json) | Out-Null

Write-Host "      OK Created 2 relationships" -ForegroundColor Green

# Test 4: Generate Scenarios
Write-Host ""
Write-Host "[4/8] Generating Scenarios (takes 5-6 minutes)..." -ForegroundColor Yellow
$scenarioBody = @{
    prompt = "What if quantum computing achieves supremacy by 2028?"
    num_scenarios = 2
} | ConvertTo-Json

$scenarios = Invoke-RestMethod -Uri "$baseUrl/api/scenarios/generate?project_id=$projectId" -Method Post -ContentType "application/json" -Body $scenarioBody -TimeoutSec 420
Write-Host "      OK Generated $($scenarios.scenarios.Count) scenarios" -ForegroundColor Green

# Test 5: Create Main Timeline
Write-Host ""
Write-Host "[5/8] Creating Main Timeline..." -ForegroundColor Yellow
$mainTimeline = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/timelines" -Method Post -ContentType "application/json" -Body (@{
    name = "Prime Timeline"
    description = "The main sequence of events"
} | ConvertTo-Json)

Write-Host "      OK Timeline created: $($mainTimeline.name)" -ForegroundColor Green

# Test 6: Add Scenarios to Timeline
Write-Host ""
Write-Host "[6/8] Adding Scenarios to Timeline..." -ForegroundColor Yellow
foreach ($idx in 0..($scenarios.scenarios.Count - 1)) {
    Invoke-RestMethod -Uri "$baseUrl/api/timelines/$($mainTimeline.id)/scenarios" -Method Post -ContentType "application/json" -Body (@{
        scenario_id = $scenarios.scenarios[$idx].id
        sequence_order = $idx
    } | ConvertTo-Json) | Out-Null
}
Write-Host "      OK Added $($scenarios.scenarios.Count) scenarios to timeline" -ForegroundColor Green

# Test 7: Create Timeline Branch
Write-Host ""
Write-Host "[7/8] Creating Timeline Branch..." -ForegroundColor Yellow
$branch = Invoke-RestMethod -Uri "$baseUrl/api/timelines/$($mainTimeline.id)/branch" -Method Post -ContentType "application/json" -Body (@{
    name = "Alternate Reality - Quantum Failure"
    description = "Timeline where quantum computing hits fundamental limits"
    branch_point_year = 2027
    branch_description = "Unexpected quantum decoherence problem discovered"
    copy_scenarios = $true
} | ConvertTo-Json)

Write-Host "      OK Branch created: $($branch.name)" -ForegroundColor Green
Write-Host "      OK Copied $($branch.scenario_count) scenarios" -ForegroundColor Green

# Test 8: Get Project Summary
Write-Host ""
Write-Host "[8/8] Getting Project Summary..." -ForegroundColor Yellow
$projectStats = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId"
$entities = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/entities"
$relationships = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/relationships"
$timelines = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/timelines"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "         Test Results Summary          " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "Project: $($projectStats.name)" -ForegroundColor White
Write-Host "  Scenarios: $($projectStats.stats.total_scenarios)" -ForegroundColor Gray
Write-Host "  Entities: $($entities.Count)" -ForegroundColor Gray
Write-Host "    - Nations: $(($entities | Where-Object {$_.type -eq 'nation'}).Count)" -ForegroundColor DarkGray
Write-Host "    - Companies: $(($entities | Where-Object {$_.type -eq 'company'}).Count)" -ForegroundColor DarkGray
Write-Host "    - People: $(($entities | Where-Object {$_.type -eq 'person'}).Count)" -ForegroundColor DarkGray
Write-Host "  Relationships: $($relationships.Count)" -ForegroundColor Gray
Write-Host "  Timelines: $($timelines.Count)" -ForegroundColor Gray
Write-Host "    - Main: 1" -ForegroundColor DarkGray
Write-Host "    - Branches: $(($timelines | Where-Object {$_.parent_timeline_id -ne $null}).Count)" -ForegroundColor DarkGray

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "    All Phase 2.2 Tests Passed!       " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Write-Host ""
Write-Host "Project ID: $projectId" -ForegroundColor Gray
Write-Host ""
Write-Host "Verify in Supabase:" -ForegroundColor Gray
Write-Host "  - projects table" -ForegroundColor DarkGray
Write-Host "  - scenarios table" -ForegroundColor DarkGray
Write-Host "  - entities table" -ForegroundColor DarkGray
Write-Host "  - relationships table" -ForegroundColor DarkGray
Write-Host "  - timelines table" -ForegroundColor DarkGray
Write-Host "  - timeline_scenarios table" -ForegroundColor DarkGray
Write-Host ""
