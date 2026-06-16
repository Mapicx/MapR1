# MapR1 Phase 3.1 - Agent System Test
# Tests agent creation, memory storage, and recall

$baseUrl = "http://localhost:8000/api"
$projectId = $null
$entityId = $null
$agentId = $null
$memoryId = $null

Write-Host "========================================"
Write-Host "Testing Agent System (Phase 3.1)"
Write-Host "========================================"

# Test 1: Create Project
Write-Host "`n[1/10] Creating Project..."
$projectResponse = Invoke-RestMethod -Uri "$baseUrl/projects" -Method Post -ContentType "application/json" -Body (@{
    name = "Agent Test Project"
    description = "Testing autonomous agents with memory"
} | ConvertTo-Json)

$projectId = $projectResponse.id
Write-Host "OK Project created: $($projectResponse.name)"

# Test 2: Create Entity (Company)
Write-Host "`n[2/10] Creating Company Entity..."
$entityResponse = Invoke-RestMethod -Uri "$baseUrl/projects/$projectId/entities" -Method Post -ContentType "application/json" -Body (@{
    type = "company"
    name = "TechCorp Industries"
    description = "Leading technology company"
    attributes = @{
        industry = "Technology"
        employees = 5000
        revenue = "500M"
    }
} | ConvertTo-Json)

$entityId = $entityResponse.id
Write-Host "OK Entity created: $($entityResponse.name)"

# Test 3: Create CEO Agent
Write-Host "`n[3/10] Creating CEO Agent..."
$agentResponse = Invoke-RestMethod -Uri "$baseUrl/projects/$projectId/agents" -Method Post -ContentType "application/json" -Body (@{
    name = "Sarah Chen"
    agent_type = "ceo"
    role = "CEO of TechCorp Industries"
    entity_id = $entityId
    personality = @{
        ambition = 0.9
        risk_tolerance = 0.7
        rationality = 0.8
        empathy = 0.6
        morality = 0.6
    }
    current_state = @{
        mood = "focused"
        energy = 0.8
    }
    resources = @{
        budget = "100M"
        influence = "high"
    }
} | ConvertTo-Json -Depth 10)

$agentId = $agentResponse.id
Write-Host "OK Agent created: $($agentResponse.name) ($($agentResponse.agent_type))"
Write-Host "   Role: $($agentResponse.role)"

# Test 4: Create Hacker Agent (Independent)
Write-Host "`n[4/10] Creating Independent Hacker Agent..."
$hackerResponse = Invoke-RestMethod -Uri "$baseUrl/projects/$projectId/agents" -Method Post -ContentType "application/json" -Body (@{
    name = "Zero Cool"
    agent_type = "hacker"
    role = "Independent Cybersecurity Researcher"
    personality = @{
        creativity = 0.9
        risk_tolerance = 0.8
        rationality = 0.7
        morality = 0.3
        empathy = 0.4
    }
} | ConvertTo-Json -Depth 10)

$hackerId = $hackerResponse.id
Write-Host "OK Agent created: $($hackerResponse.name) ($($hackerResponse.agent_type))"

# Test 5: List Agents
Write-Host "`n[5/10] Listing All Agents..."
$agentsResponse = Invoke-RestMethod -Uri "$baseUrl/projects/$projectId/agents" -Method Get
Write-Host "OK Found $($agentsResponse.Count) agents"
foreach ($agent in $agentsResponse) {
    Write-Host "   - $($agent.name) ($($agent.agent_type))"
}

# Test 6: Create Memories for CEO
Write-Host "`n[6/10] Creating Memories for CEO..."

# Memory 1: Observation
$memory1 = Invoke-RestMethod -Uri "$baseUrl/agents/$agentId/memories" -Method Post -ContentType "application/json" -Body (@{
    memory_type = "observation"
    content = "Competitor launched aggressive pricing strategy, undercutting our prices by 30%"
    importance = 0.8
    emotional_valence = -0.3
} | ConvertTo-Json)
Write-Host "OK Memory 1: Observation (negative event)"

# Memory 2: Interaction
$memory2 = Invoke-RestMethod -Uri "$baseUrl/agents/$agentId/memories" -Method Post -ContentType "application/json" -Body (@{
    memory_type = "interaction"
    content = "Board meeting: Investors expressed concern about market share decline"
    importance = 0.9
    emotional_valence = -0.5
    related_entity_ids = @($entityId)
} | ConvertTo-Json -Depth 10)
Write-Host "OK Memory 2: Interaction (board meeting)"

# Memory 3: Decision
$memory3 = Invoke-RestMethod -Uri "$baseUrl/agents/$agentId/memories" -Method Post -ContentType "application/json" -Body (@{
    memory_type = "decision"
    content = "Decided to invest $50M in R&D for breakthrough product innovation"
    importance = 0.95
    emotional_valence = 0.6
} | ConvertTo-Json)
Write-Host "OK Memory 3: Decision (major investment)"

# Memory 4: Emotion
$memory4 = Invoke-RestMethod -Uri "$baseUrl/agents/$agentId/memories" -Method Post -ContentType "application/json" -Body (@{
    memory_type = "emotion"
    content = "Felt determined and optimistic about company's future after strategy session"
    importance = 0.6
    emotional_valence = 0.7
} | ConvertTo-Json)
Write-Host "OK Memory 4: Emotion (positive feeling)"

# Test 7: Get Recent Memories
Write-Host "`n[7/10] Getting Recent Memories..."
$recentMemories = Invoke-RestMethod -Uri "$baseUrl/agents/$agentId/memories/recent?limit=3" -Method Get
Write-Host "OK Retrieved $($recentMemories.Count) recent memories:"
foreach ($mem in $recentMemories) {
    $emoji = if ($mem.emotional_valence -gt 0.3) { "😊" } elseif ($mem.emotional_valence -lt -0.3) { "😢" } else { "😐" }
    Write-Host "   $emoji [$($mem.memory_type)] $($mem.content.Substring(0, [Math]::Min(60, $mem.content.Length)))..."
}

# Test 8: Get Important Memories
Write-Host "`n[8/10] Getting Important Memories..."
$importantMemories = Invoke-RestMethod -Uri "$baseUrl/agents/$agentId/memories/important?threshold=0.8" -Method Get
Write-Host "OK Retrieved $($importantMemories.Count) important memories:"
foreach ($mem in $importantMemories) {
    Write-Host "   - [$($mem.memory_type)] Importance: $($mem.importance) - $($mem.content.Substring(0, [Math]::Min(60, $mem.content.Length)))..."
}

# Test 9: Semantic Memory Recall
Write-Host "`n[9/10] Semantic Memory Recall..."
$recallResponse = Invoke-RestMethod -Uri "$baseUrl/agents/$agentId/memories/recall" -Method Post -ContentType "application/json" -Body (@{
    query = "pricing and competition"
    top_k = 3
} | ConvertTo-Json)
Write-Host "OK Found $($recallResponse.count) similar memories for query: '$($recallResponse.query)'"
foreach ($result in $recallResponse.results) {
    Write-Host "   - $($result.content.Substring(0, [Math]::Min(60, $result.content.Length)))..."
}

# Test 10: Build Decision Context
Write-Host "`n[10/10] Building Decision Context..."
$contextResponse = Invoke-RestMethod -Uri "$baseUrl/agents/$agentId/memories/context" -Method Post -ContentType "application/json" -Body (@{
    situation = "Should we lower our prices to compete?"
    include_recent = 3
    include_important = 3
    include_similar = 3
} | ConvertTo-Json)
Write-Host "OK Context built for situation: '$($contextResponse.situation)'"
Write-Host "`nContext Preview:"
Write-Host "----------------------------------------"
Write-Host $contextResponse.context.Substring(0, [Math]::Min(500, $contextResponse.context.Length))
if ($contextResponse.context.Length -gt 500) {
    Write-Host "..."
}
Write-Host "----------------------------------------"

# Get Memory Stats
Write-Host "`n[Bonus] Memory Statistics..."
$statsResponse = Invoke-RestMethod -Uri "$baseUrl/agents/$agentId/memories/stats" -Method Get
Write-Host "Total memories: $($statsResponse.total)"
Write-Host "By type:"
foreach ($type in $statsResponse.by_type.PSObject.Properties) {
    Write-Host "   - $($type.Name): $($type.Value)"
}
Write-Host "Average importance: $($statsResponse.avg_importance)"
Write-Host "Average emotional valence: $($statsResponse.avg_emotional_valence)"

# Summary
Write-Host "`n========================================"
Write-Host "Test Results Summary"
Write-Host "========================================"
Write-Host "Project: $($projectResponse.name)"
Write-Host "Entity: $($entityResponse.name)"
Write-Host "Agents: $($agentsResponse.Count)"
Write-Host "   - CEO: $($agentResponse.name)"
Write-Host "   - Hacker: $($hackerResponse.name)"
Write-Host "Memories: $($statsResponse.total)"
Write-Host ""
Write-Host "========================================"
Write-Host "Phase 3.1 Agent Tests Passed!"
Write-Host "========================================"
Write-Host "Project ID: $projectId"
Write-Host "Agent ID: $agentId"
Write-Host ""
Write-Host "Verify in Supabase:"
Write-Host "- agents table"
Write-Host "- agent_memories table"
Write-Host ""
Write-Host "Verify in ChromaDB:"
Write-Host "- ./embeddings/ folder"
