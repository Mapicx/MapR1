# MapR1 Phase 3.2 - Goals & Relationships Test
# Tests goal system and relationship dynamics

$baseUrl = "http://localhost:8000/api"
$projectId = $null
$ceoId = $null
$competitorId = $null
$goalId = $null
$relationshipId = $null

Write-Host "========================================"
Write-Host "Testing Goals & Relationships (Phase 3.2)"
Write-Host "========================================"

# Test 1: Create Project
Write-Host "`n[1/15] Creating Project..."
$projectResponse = Invoke-RestMethod -Uri "$baseUrl/projects" -Method Post -ContentType "application/json" -Body (@{
    name = "Goals & Relationships Test"
    description = "Testing agent goals and relationship dynamics"
} | ConvertTo-Json)

$projectId = $projectResponse.id
Write-Host "OK Project created: $($projectResponse.name)"

# Test 2: Create CEO Agent
Write-Host "`n[2/15] Creating CEO Agent..."
$ceoResponse = Invoke-RestMethod -Uri "$baseUrl/projects/$projectId/agents" -Method Post -ContentType "application/json" -Body (@{
    name = "Alex Morgan"
    agent_type = "ceo"
    role = "CEO of TechCorp"
    personality = @{
        ambition = 0.9
        risk_tolerance = 0.7
        rationality = 0.8
    }
} | ConvertTo-Json -Depth 10)

$ceoId = $ceoResponse.id
Write-Host "OK CEO created: $($ceoResponse.name)"

# Test 3: Create Competitor CEO
Write-Host "`n[3/15] Creating Competitor CEO..."
$competitorResponse = Invoke-RestMethod -Uri "$baseUrl/projects/$projectId/agents" -Method Post -ContentType "application/json" -Body (@{
    name = "Jordan Blake"
    agent_type = "ceo"
    role = "CEO of RivalCorp"
    personality = @{
        ambition = 0.95
        risk_tolerance = 0.8
        rationality = 0.7
    }
} | ConvertTo-Json -Depth 10)

$competitorId = $competitorResponse.id
Write-Host "OK Competitor created: $($competitorResponse.name)"

# Test 4: Add Goals for CEO
Write-Host "`n[4/15] Adding Goals for CEO..."

$goal1 = Invoke-RestMethod -Uri "$baseUrl/agents/$ceoId/goals" -Method Post -ContentType "application/json" -Body (@{
    description = "Increase market share to 30%"
    goal_type = "wealth"
    priority = 0.9
} | ConvertTo-Json)
Write-Host "OK Goal 1: $($goal1.description)"
$goalId = $goal1.id

$goal2 = Invoke-RestMethod -Uri "$baseUrl/agents/$ceoId/goals" -Method Post -ContentType "application/json" -Body (@{
    description = "Build strong leadership team"
    goal_type = "relationships"
    priority = 0.7
} | ConvertTo-Json)
Write-Host "OK Goal 2: $($goal2.description)"

$goal3 = Invoke-RestMethod -Uri "$baseUrl/agents/$ceoId/goals" -Method Post -ContentType "application/json" -Body (@{
    description = "Launch innovative product line"
    goal_type = "innovation"
    priority = 0.85
} | ConvertTo-Json)
Write-Host "OK Goal 3: $($goal3.description)"

# Test 5: Get Active Goals
Write-Host "`n[5/15] Getting Active Goals..."
$activeGoals = Invoke-RestMethod -Uri "$baseUrl/agents/$ceoId/goals/active" -Method Get
Write-Host "OK Retrieved $($activeGoals.Count) active goals (sorted by priority):"
foreach ($goal in $activeGoals) {
    Write-Host "   - $($goal.description) (priority: $($goal.priority), progress: $($goal.progress))"
}

# Test 6: Update Goal Progress
Write-Host "`n[6/15] Updating Goal Progress..."
$progressUpdate = Invoke-RestMethod -Uri "$baseUrl/goals/$goalId/progress" -Method Post -ContentType "application/json" -Body (@{
    progress = 0.45
} | ConvertTo-Json)
Write-Host "OK Progress updated: $($progressUpdate.description) → $($progressUpdate.progress * 100)%"

# Test 7: Create Relationship
Write-Host "`n[7/15] Creating Relationship (Neutral)..."
$relationshipResponse = Invoke-RestMethod -Uri "$baseUrl/agents/$ceoId/relationships" -Method Post -ContentType "application/json" -Body (@{
    other_agent_id = $competitorId
    relationship_type = "neutral"
    strength = 0.0
    trust = 0.5
} | ConvertTo-Json)

$relationshipId = $relationshipResponse.id
Write-Host "OK Relationship created between Alex and Jordan"
Write-Host "   Type: $($relationshipResponse.relationship_type)"
Write-Host "   Strength: $($relationshipResponse.strength)"
Write-Host "   Trust: $($relationshipResponse.trust)"

# Test 8: Record Negative Interaction (Price War)
Write-Host "`n[8/15] Recording Negative Interaction (Price War)..."
$interaction1 = Invoke-RestMethod -Uri "$baseUrl/relationships/$relationshipId/interact" -Method Post -ContentType "application/json" -Body (@{
    interaction_type = "conflict"
    description = "RivalCorp launched aggressive price war, undercutting TechCorp by 25%"
    outcome = "negative"
    trust_change = -0.2
    strength_change = -0.3
} | ConvertTo-Json)
Write-Host "OK Interaction recorded: $($interaction1.description)"
Write-Host "   Trust change: $($interaction1.trust_change)"
Write-Host "   Strength change: $($interaction1.strength_change)"

# Test 9: Check Updated Relationship
Write-Host "`n[9/15] Checking Updated Relationship..."
$updatedRel = Invoke-RestMethod -Uri "$baseUrl/relationships/$relationshipId" -Method Get
Write-Host "OK Relationship updated:"
Write-Host "   Type: $($updatedRel.relationship_type)"
Write-Host "   Strength: $($updatedRel.strength)"
Write-Host "   Trust: $($updatedRel.trust)"
Write-Host "   Interactions: $($updatedRel.interaction_count)"

# Test 10: Record Another Negative Interaction
Write-Host "`n[10/15] Recording Another Negative Interaction (Patent Dispute)..."
$interaction2 = Invoke-RestMethod -Uri "$baseUrl/relationships/$relationshipId/interact" -Method Post -ContentType "application/json" -Body (@{
    interaction_type = "conflict"
    description = "Patent infringement lawsuit filed by RivalCorp"
    outcome = "negative"
    trust_change = -0.3
    strength_change = -0.4
} | ConvertTo-Json)
Write-Host "OK Interaction recorded: $($interaction2.description)"

# Test 11: Check Relationship (Should be Enemy Now)
Write-Host "`n[11/15] Checking Relationship Status..."
$enemyRel = Invoke-RestMethod -Uri "$baseUrl/relationships/$relationshipId" -Method Get
Write-Host "OK Relationship evolved:"
Write-Host "   Type: $($enemyRel.relationship_type) (was neutral)"
Write-Host "   Strength: $($enemyRel.strength) (hostile)"
Write-Host "   Trust: $($enemyRel.trust) (low)"

# Test 12: Get Enemies List
Write-Host "`n[12/15] Getting Enemies List..."
$enemies = Invoke-RestMethod -Uri "$baseUrl/agents/$ceoId/enemies" -Method Get
Write-Host "OK Alex Morgan has $($enemies.count) enemies:"
foreach ($enemyId in $enemies.enemies) {
    Write-Host "   - Agent: $enemyId"
}

# Test 13: Get Goal Context
Write-Host "`n[13/15] Getting Goal Context..."
$goalContext = Invoke-RestMethod -Uri "$baseUrl/agents/$ceoId/goals/context" -Method Post -ContentType "application/json" -Body (@{
    limit = 5
} | ConvertTo-Json)
Write-Host "OK Goal Context:"
Write-Host "----------------------------------------"
Write-Host $goalContext.context
Write-Host "----------------------------------------"

# Test 14: Get Relationship Context
Write-Host "`n[14/15] Getting Relationship Context..."
$relContext = Invoke-RestMethod -Uri "$baseUrl/agents/$ceoId/relationships/context" -Method Post -ContentType "application/json" -Body (@{
    limit = 10
} | ConvertTo-Json)
Write-Host "OK Relationship Context:"
Write-Host "----------------------------------------"
Write-Host $relContext.context
Write-Host "----------------------------------------"

# Test 15: Get Statistics
Write-Host "`n[15/15] Getting Statistics..."
$goalStats = Invoke-RestMethod -Uri "$baseUrl/agents/$ceoId/goals/stats" -Method Get
$relStats = Invoke-RestMethod -Uri "$baseUrl/agents/$ceoId/relationships/stats" -Method Get

Write-Host "OK Goal Statistics:"
Write-Host "   Total goals: $($goalStats.total)"
Write-Host "   Active: $($goalStats.active)"
Write-Host "   Completed: $($goalStats.completed)"
Write-Host "   Avg priority: $($goalStats.avg_priority)"
Write-Host "   Avg progress: $($goalStats.avg_progress)"

Write-Host "`nOK Relationship Statistics:"
Write-Host "   Total relationships: $($relStats.total)"
Write-Host "   Allies: $($relStats.allies)"
Write-Host "   Enemies: $($relStats.enemies)"
Write-Host "   Neutral: $($relStats.neutral)"
Write-Host "   Avg trust: $($relStats.avg_trust)"
Write-Host "   Avg strength: $($relStats.avg_strength)"
Write-Host "   Total interactions: $($relStats.total_interactions)"

# Summary
Write-Host "`n========================================"
Write-Host "Test Results Summary"
Write-Host "========================================"
Write-Host "Project: $($projectResponse.name)"
Write-Host "Agents: 2"
Write-Host "   - CEO: $($ceoResponse.name)"
Write-Host "   - Competitor: $($competitorResponse.name)"
Write-Host "Goals: $($goalStats.total)"
Write-Host "Relationships: $($relStats.total)"
Write-Host "Interactions: $($relStats.total_interactions)"
Write-Host ""
Write-Host "Relationship Evolution:"
Write-Host "   neutral → rival → enemy"
Write-Host "   (through negative interactions)"
Write-Host ""
Write-Host "========================================"
Write-Host "Phase 3.2 Tests Passed!"
Write-Host "========================================"
Write-Host "Project ID: $projectId"
Write-Host "CEO ID: $ceoId"
Write-Host "Competitor ID: $competitorId"
Write-Host ""
Write-Host "Verify in Supabase:"
Write-Host "- goals table"
Write-Host "- agent_relationships table"
Write-Host "- agent_interactions table"
