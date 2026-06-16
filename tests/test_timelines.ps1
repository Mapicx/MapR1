# Test Timeline Branching System
Write-Host "`n=== Testing Timeline Branching ===" -ForegroundColor Cyan

$baseUrl = "http://localhost:8000"

# 1. Create a project
Write-Host "`n1. Creating Project..." -ForegroundColor Yellow
$projectBody = @{
    name = "Timeline Test Project"
    description = "Testing timeline branching"
} | ConvertTo-Json

$project = Invoke-RestMethod -Uri "$baseUrl/api/projects" -Method Post -ContentType "application/json" -Body $projectBody
$projectId = $project.id
Write-Host "   Project ID: $projectId" -ForegroundColor Green

# 2. Generate some scenarios
Write-Host "`n2. Generating Scenarios (takes 1-2 minutes)..." -ForegroundColor Yellow
$scenarioBody = @{
    prompt = "What if fusion energy becomes commercially viable by 2030?"
    num_scenarios = 2
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "$baseUrl/api/scenarios/generate?project_id=$projectId" -Method Post -ContentType "application/json" -Body $scenarioBody -TimeoutSec 180
$scenario1Id = $response.scenarios[0].id
$scenario2Id = $response.scenarios[1].id
Write-Host "   Generated 2 scenarios" -ForegroundColor Green

# 3. Create main timeline
Write-Host "`n3. Creating Main Timeline..." -ForegroundColor Yellow
$timelineBody = @{
    name = "Main Timeline"
    description = "The primary timeline"
} | ConvertTo-Json

$mainTimeline = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/timelines" -Method Post -ContentType "application/json" -Body $timelineBody
$mainTimelineId = $mainTimeline.id
Write-Host "   Timeline: $($mainTimeline.name)" -ForegroundColor Green
Write-Host "   ID: $mainTimelineId" -ForegroundColor Green

# 4. Add scenarios to main timeline
Write-Host "`n4. Adding Scenarios to Timeline..." -ForegroundColor Yellow
$addScenario1 = @{
    scenario_id = $scenario1Id
    sequence_order = 0
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/api/timelines/$mainTimelineId/scenarios" -Method Post -ContentType "application/json" -Body $addScenario1
Write-Host "   Added scenario 1" -ForegroundColor Green

$addScenario2 = @{
    scenario_id = $scenario2Id
    sequence_order = 1
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/api/timelines/$mainTimelineId/scenarios" -Method Post -ContentType "application/json" -Body $addScenario2
Write-Host "   Added scenario 2" -ForegroundColor Green

# 5. Get timeline with scenarios
Write-Host "`n5. Getting Timeline Details..." -ForegroundColor Yellow
$timeline = Invoke-RestMethod -Uri "$baseUrl/api/timelines/$mainTimelineId"
Write-Host "   Name: $($timeline.name)" -ForegroundColor Green
Write-Host "   Scenarios: $($timeline.scenario_count)" -ForegroundColor Green

# 6. Create a branch
Write-Host "`n6. Creating Timeline Branch..." -ForegroundColor Yellow
$branchBody = @{
    name = "Alternate Timeline - Energy Crisis"
    description = "What if fusion energy fails?"
    branch_point_year = 2028
    branch_description = "Fusion reactor prototype fails catastrophically"
    copy_scenarios = $true
} | ConvertTo-Json

$branch = Invoke-RestMethod -Uri "$baseUrl/api/timelines/$mainTimelineId/branch" -Method Post -ContentType "application/json" -Body $branchBody
$branchId = $branch.id
Write-Host "   Branch: $($branch.name)" -ForegroundColor Green
Write-Host "   Branch ID: $branchId" -ForegroundColor Green
Write-Host "   Parent: $($branch.parent_timeline_id)" -ForegroundColor Green
Write-Host "   Branch Point: $($branch.branch_point_year)" -ForegroundColor Green
Write-Host "   Copied Scenarios: $($branch.scenario_count)" -ForegroundColor Green

# 7. List all timelines
Write-Host "`n7. Listing All Timelines..." -ForegroundColor Yellow
$timelines = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/timelines"
Write-Host "   Total timelines: $($timelines.Count)" -ForegroundColor Green
foreach ($t in $timelines) {
    $parentInfo = if ($t.parent_timeline_id) { " (branch from $($t.parent_timeline_id))" } else { " (main)" }
    Write-Host "   - $($t.name)$parentInfo - $($t.scenario_count) scenarios" -ForegroundColor Gray
}

# 8. Get scenarios in branch
Write-Host "`n8. Getting Branch Scenarios..." -ForegroundColor Yellow
$branchScenarios = Invoke-RestMethod -Uri "$baseUrl/api/timelines/$branchId/scenarios"
Write-Host "   Scenarios in branch: $($branchScenarios.scenarios.Count)" -ForegroundColor Green
foreach ($s in $branchScenarios.scenarios) {
    Write-Host "   - $($s.title)" -ForegroundColor Gray
}

# 9. Create another branch
Write-Host "`n9. Creating Second Branch..." -ForegroundColor Yellow
$branch2Body = @{
    name = "Alternate Timeline - Rapid Adoption"
    description = "What if fusion energy is adopted faster than expected?"
    branch_point_year = 2029
    branch_description = "Breakthrough in fusion efficiency leads to rapid global adoption"
    copy_scenarios = $false
} | ConvertTo-Json

$branch2 = Invoke-RestMethod -Uri "$baseUrl/api/timelines/$mainTimelineId/branch" -Method Post -ContentType "application/json" -Body $branch2Body
Write-Host "   Branch: $($branch2.name)" -ForegroundColor Green
Write-Host "   Scenarios: $($branch2.scenario_count) (not copied)" -ForegroundColor Green

# 10. List all timelines again
Write-Host "`n10. Final Timeline List..." -ForegroundColor Yellow
$finalTimelines = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/timelines"
Write-Host "   Total timelines: $($finalTimelines.Count)" -ForegroundColor Green

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Timeline Branching Tests Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nProject ID: $projectId" -ForegroundColor Gray
Write-Host "Main Timeline ID: $mainTimelineId" -ForegroundColor Gray
Write-Host "Branch 1 ID: $branchId" -ForegroundColor Gray
Write-Host "Branch 2 ID: $($branch2.id)" -ForegroundColor Gray
Write-Host "`nCheck Supabase for timelines and timeline_scenarios tables`n" -ForegroundColor Gray
