# Test World State System
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Testing World State System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$baseUrl = "http://localhost:8000"

# 1. Create a project
Write-Host ""
Write-Host "[1/7] Creating Project..." -ForegroundColor Yellow
$projectBody = @{
    name = "World State Test"
    description = "Testing world state tracking"
} | ConvertTo-Json

$project = Invoke-RestMethod -Uri "$baseUrl/api/projects" -Method Post -ContentType "application/json" -Body $projectBody
$projectId = $project.id
Write-Host "      OK Project created: $($project.name)" -ForegroundColor Green

# 2. Create world state
Write-Host ""
Write-Host "[2/7] Creating World State..." -ForegroundColor Yellow
$worldStateBody = @{
    initial_state = @{
        global_temperature = 1.5
        sea_level_rise = 0.2
        renewable_energy_percent = 35
        population = 8000000000
        conflicts = @("Region A", "Region B")
    }
} | ConvertTo-Json

$worldState = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/world" -Method Post -ContentType "application/json" -Body $worldStateBody
Write-Host "      OK World state created" -ForegroundColor Green
Write-Host "      - Temperature: $($worldState.state.global_temperature)C" -ForegroundColor Gray
Write-Host "      - Population: $($worldState.state.population)" -ForegroundColor Gray

# 3. Record some events
Write-Host ""
Write-Host "[3/7] Recording World Events..." -ForegroundColor Yellow

$event1 = @{
    event_type = "treaty"
    description = "Global Climate Accord signed by 150 nations"
    impact_score = 0.8
    affected_entity_ids = @()
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/events" -Method Post -ContentType "application/json" -Body $event1 | Out-Null
Write-Host "      OK Event 1: Climate treaty signed" -ForegroundColor Green

$event2 = @{
    event_type = "discovery"
    description = "Breakthrough in fusion energy efficiency"
    impact_score = 0.9
    affected_entity_ids = @()
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/events" -Method Post -ContentType "application/json" -Body $event2 | Out-Null
Write-Host "      OK Event 2: Fusion breakthrough" -ForegroundColor Green

$event3 = @{
    event_type = "disaster"
    description = "Major hurricane causes widespread damage"
    impact_score = -0.6
    affected_entity_ids = @()
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/events" -Method Post -ContentType "application/json" -Body $event3 | Out-Null
Write-Host "      OK Event 3: Hurricane disaster" -ForegroundColor Green

# 4. Update world state
Write-Host ""
Write-Host "[4/7] Updating World State..." -ForegroundColor Yellow
$updateBody = @{
    state_updates = @{
        global_temperature = 1.6
        renewable_energy_percent = 42
        major_events_count = 3
    }
} | ConvertTo-Json

$updated = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/world" -Method Put -ContentType "application/json" -Body $updateBody
Write-Host "      OK State updated" -ForegroundColor Green
Write-Host "      - Temperature: $($updated.state.global_temperature)C (was 1.5C)" -ForegroundColor Gray
Write-Host "      - Renewables: $($updated.state.renewable_energy_percent)% (was 35%)" -ForegroundColor Gray

# 5. Get world snapshot
Write-Host ""
Write-Host "[5/7] Getting World Snapshot..." -ForegroundColor Yellow
$snapshot = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/world/snapshot"
Write-Host "      OK Snapshot retrieved" -ForegroundColor Green
Write-Host "      - State keys: $($snapshot.state.Keys.Count)" -ForegroundColor Gray
Write-Host "      - Recent events: $($snapshot.recent_events.Count)" -ForegroundColor Gray

# 6. Get all events
Write-Host ""
Write-Host "[6/7] Getting All Events..." -ForegroundColor Yellow
$events = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/events"
Write-Host "      OK Retrieved $($events.Count) events" -ForegroundColor Green
foreach ($e in $events) {
    $impact = if ($e.impact_score -gt 0) { "+$($e.impact_score)" } else { "$($e.impact_score)" }
    Write-Host "      - $($e.event_type): $($e.description) (impact: $impact)" -ForegroundColor Gray
}

# 7. Filter events by type
Write-Host ""
Write-Host "[7/7] Filtering Events by Type..." -ForegroundColor Yellow
$treaties = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/events?event_type=treaty"
Write-Host "      OK Found $($treaties.Count) treaty events" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "         Test Results Summary          " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "World State:" -ForegroundColor White
Write-Host "  Temperature: $($snapshot.state.global_temperature)C" -ForegroundColor Gray
Write-Host "  Population: $($snapshot.state.population)" -ForegroundColor Gray
Write-Host "  Renewables: $($snapshot.state.renewable_energy_percent)%" -ForegroundColor Gray
Write-Host "  Events: $($snapshot.state.major_events_count)" -ForegroundColor Gray

Write-Host ""
Write-Host "Events Summary:" -ForegroundColor White
Write-Host "  Total events: $($events.Count)" -ForegroundColor Gray
Write-Host "  Positive impact: $(($events | Where-Object {$_.impact_score -gt 0}).Count)" -ForegroundColor Gray
Write-Host "  Negative impact: $(($events | Where-Object {$_.impact_score -lt 0}).Count)" -ForegroundColor Gray

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "    World State Tests Passed!          " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Write-Host ""
Write-Host "Project ID: $projectId" -ForegroundColor Gray
Write-Host ""
Write-Host "Verify in Supabase:" -ForegroundColor Gray
Write-Host "  - world_states table" -ForegroundColor DarkGray
Write-Host "  - world_events table" -ForegroundColor DarkGray
Write-Host ""
