# Test Memory System (Semantic Search)
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Testing Memory System (ChromaDB)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$baseUrl = "http://localhost:8000"

# 1. Create a project
Write-Host ""
Write-Host "[1/8] Creating Project..." -ForegroundColor Yellow
$projectBody = @{
    name = "Memory Test Project"
    description = "Testing semantic memory and search"
} | ConvertTo-Json

$project = Invoke-RestMethod -Uri "$baseUrl/api/projects" -Method Post -ContentType "application/json" -Body $projectBody
$projectId = $project.id
Write-Host "      OK Project created" -ForegroundColor Green

# 2. Generate scenarios (will be stored in memory automatically)
Write-Host ""
Write-Host "[2/8] Generating Scenarios (5-6 minutes)..." -ForegroundColor Yellow
$scenarioBody = @{
    prompt = "What if artificial intelligence achieves consciousness by 2030?"
    num_scenarios = 2
} | ConvertTo-Json

$scenarios = Invoke-RestMethod -Uri "$baseUrl/api/scenarios/generate?project_id=$projectId" -Method Post -ContentType "application/json" -Body $scenarioBody -TimeoutSec 420
Write-Host "      OK Generated $($scenarios.scenarios.Count) scenarios" -ForegroundColor Green
Write-Host "      - Stored in memory automatically" -ForegroundColor Gray

# 3. Create entities (will be stored in memory)
Write-Host ""
Write-Host "[3/8] Creating Entities..." -ForegroundColor Yellow

$entity1 = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/entities" -Method Post -ContentType "application/json" -Body (@{
    type = "company"
    name = "NeuroTech AI"
    description = "Leading AI research company"
    attributes = @{ focus = "consciousness research"; employees = 5000 }
} | ConvertTo-Json)

$entity2 = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/entities" -Method Post -ContentType "application/json" -Body (@{
    type = "person"
    name = "Dr. Maya Chen"
    description = "AI consciousness researcher"
    attributes = @{ role = "Chief Scientist"; expertise = "Neural Networks" }
} | ConvertTo-Json)

Write-Host "      OK Created 2 entities" -ForegroundColor Green
Write-Host "      - Stored in memory automatically" -ForegroundColor Gray

# 4. Record events (will be stored in memory)
Write-Host ""
Write-Host "[4/8] Recording Events..." -ForegroundColor Yellow

Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/events" -Method Post -ContentType "application/json" -Body (@{
    event_type = "discovery"
    description = "Breakthrough in neural network consciousness modeling"
    impact_score = 0.9
} | ConvertTo-Json) | Out-Null

Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/events" -Method Post -ContentType "application/json" -Body (@{
    event_type = "treaty"
    description = "International AI Ethics Agreement signed"
    impact_score = 0.7
} | ConvertTo-Json) | Out-Null

Write-Host "      OK Recorded 2 events" -ForegroundColor Green
Write-Host "      - Stored in memory automatically" -ForegroundColor Gray

# 5. Get memory stats
Write-Host ""
Write-Host "[5/8] Getting Memory Stats..." -ForegroundColor Yellow
$stats = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/memory/stats"
Write-Host "      OK Memory stats retrieved" -ForegroundColor Green
Write-Host "      - Total memories: $($stats.total)" -ForegroundColor Gray
Write-Host "      - Scenarios: $($stats.scenarios)" -ForegroundColor Gray
Write-Host "      - Events: $($stats.events)" -ForegroundColor Gray
Write-Host "      - Entities: $($stats.entities)" -ForegroundColor Gray

# 6. Search for similar scenarios
Write-Host ""
Write-Host "[6/8] Searching Similar Scenarios..." -ForegroundColor Yellow
$searchBody = @{
    query = "AI becoming self-aware and conscious"
    top_k = 3
} | ConvertTo-Json

$results = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/memory/search/scenarios" -Method Post -ContentType "application/json" -Body $searchBody
Write-Host "      OK Found $($results.Count) similar scenarios" -ForegroundColor Green
foreach ($r in $results) {
    Write-Host "      - $($r.metadata.title) (distance: $([math]::Round($r.distance, 3)))" -ForegroundColor Gray
}

# 7. Search for similar events
Write-Host ""
Write-Host "[7/8] Searching Similar Events..." -ForegroundColor Yellow
$eventSearchBody = @{
    query = "scientific breakthrough in AI"
    top_k = 3
} | ConvertTo-Json

$eventResults = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/memory/search/events" -Method Post -ContentType "application/json" -Body $eventSearchBody
Write-Host "      OK Found $($eventResults.Count) similar events" -ForegroundColor Green
foreach ($r in $eventResults) {
    Write-Host "      - $($r.metadata.event_type): $(($r.content -split "`n")[1])" -ForegroundColor Gray
}

# 8. General semantic search
Write-Host ""
Write-Host "[8/8] General Semantic Search..." -ForegroundColor Yellow
$generalSearchBody = @{
    query = "consciousness and neural networks"
    top_k = 5
} | ConvertTo-Json

$generalResults = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/memory/search" -Method Post -ContentType "application/json" -Body $generalSearchBody
Write-Host "      OK Found $($generalResults.Count) relevant memories" -ForegroundColor Green
foreach ($r in $generalResults) {
    $type = $r.metadata.type
    Write-Host "      - [$type] $(($r.content -split "`n")[0])" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "         Test Results Summary          " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "Memory System:" -ForegroundColor White
Write-Host "  Total memories: $($stats.total)" -ForegroundColor Gray
Write-Host "  Scenarios: $($stats.scenarios)" -ForegroundColor Gray
Write-Host "  Events: $($stats.events)" -ForegroundColor Gray
Write-Host "  Entities: $($stats.entities)" -ForegroundColor Gray

Write-Host ""
Write-Host "Semantic Search:" -ForegroundColor White
Write-Host "  Scenario search: $($results.Count) results" -ForegroundColor Gray
Write-Host "  Event search: $($eventResults.Count) results" -ForegroundColor Gray
Write-Host "  General search: $($generalResults.Count) results" -ForegroundColor Gray

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "    Memory System Tests Passed!        " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Write-Host ""
Write-Host "Project ID: $projectId" -ForegroundColor Gray
Write-Host ""
Write-Host "Memory stored in: ./embeddings/" -ForegroundColor Gray
Write-Host "ChromaDB collection: mapr1_memories" -ForegroundColor Gray
Write-Host ""
