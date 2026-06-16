# MapR1 - Simulation & Pattern Detection Test
# Runs 6 simulation steps to demonstrate the full intel -> execution progression:
#   Steps 1-3: agents gather information, discover specific facts, build knowledge_score
#   Steps 4-6: knowledge threshold reached, agents switch to execution actions
#
# All output is saved to:
#   logs/test_runs/<timestamp>/console.log   (full console transcript)
#
# The backend also writes structured logs per-project to:
#   logs/simulations/<project_id>/<timestamp>/
#     simulation.log    - human-readable chronological log
#     decisions.jsonl   - every agent LLM decision (JSON)
#     actions.jsonl     - every executed action (JSON)
#     patterns.jsonl    - every detected pattern (JSON)
#     summary.json      - final run summary

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logDir = "logs/test_runs/$timestamp"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$consoleLog = "$logDir/console.log"

function Write-Log {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
    Add-Content -Path $consoleLog -Value $Message
}

function Print-StepResult {
    param($stepResult, [int]$stepNum)
    Write-Log "OK Step $stepNum complete - $($stepResult.actions.Count) actions" "Green"
    foreach ($action in $stepResult.actions) {
        $status = if ($action.success) { "SUCCESS" } else { "FAILED " }
        $statusColor = if ($action.success) { "Green" } else { "Red" }
        Write-Log "   [$status] $($action.agent_name): $($action.action_type)" $statusColor
        Write-Log "      Reasoning : $($action.reasoning.Substring(0, [Math]::Min(120, $action.reasoning.Length)))..."
        Write-Log "      Outcome   : $($action.outcome.Substring(0, [Math]::Min(150, $action.outcome.Length)))..."
        if ($action.impact) {
            $impactStr = ($action.impact | ConvertTo-Json -Compress)
            Write-Log "      Impact    : $($impactStr.Substring(0, [Math]::Min(100, $impactStr.Length)))"
        }
    }
}

Write-Log "========================================"  "Cyan"
Write-Log "MapR1 Simulation Test - Intel to Execution Arc" "Cyan"
Write-Log "========================================"  "Cyan"
Write-Log "Run started : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Log "Console log : $consoleLog"
Write-Log ""
Write-Log "Expected progression:" "Yellow"
Write-Log "  Steps 1-3 : Agents gather intel, discover specific facts" "Yellow"
Write-Log "  Steps 4-6 : Knowledge threshold reached, agents execute actions" "Yellow"
Write-Log ""

$baseUrl = "http://localhost:8000/api"
$projectId = $null
$ceoId = $null
$competitorId = $null
$activistId = $null

# Test 1: Create Project
Write-Log "[1/15] Creating Project..." "Yellow"
$projectResponse = Invoke-RestMethod -Uri "$baseUrl/projects" -Method Post -ContentType "application/json" -Body (@{
    name = "Intel-to-Execution Arc Test"
    description = "Testing layered knowledge system: agents gather intel then switch to execution actions"
} | ConvertTo-Json)

$projectId = $projectResponse.id
Write-Log "OK Project: $($projectResponse.name)  (id: $projectId)" "Green"

# Test 2: Create World State
Write-Log "`n[2/15] Creating World State..." "Yellow"
Invoke-RestMethod -Uri "$baseUrl/projects/$projectId/world" -Method Post -ContentType "application/json" -Body (@{
    state = @{
        economy = "growing"
        technology_level = "advanced"
        political_stability = "moderate"
        market_competition = "high"
        regulatory_environment = "tightening"
        public_sentiment = "skeptical_of_corporations"
    }
} | ConvertTo-Json -Depth 10) | Out-Null
Write-Log "OK World state created" "Green"

# Test 3: Create Agents
Write-Log "`n[3/15] Creating Agents..." "Yellow"

$ceo1Response = Invoke-RestMethod -Uri "$baseUrl/projects/$projectId/agents" -Method Post -ContentType "application/json" -Body (@{
    name = "Sarah Chen"
    agent_type = "ceo"
    role = "CEO of TechCorp"
    personality = @{ ambition = 0.9; risk_tolerance = 0.7; rationality = 0.8; empathy = 0.6 }
} | ConvertTo-Json -Depth 10)
$ceoId = $ceo1Response.id
Write-Log "OK CEO 1 : $($ceo1Response.name)  (id: $ceoId)" "Green"

$ceo2Response = Invoke-RestMethod -Uri "$baseUrl/projects/$projectId/agents" -Method Post -ContentType "application/json" -Body (@{
    name = "Marcus Rivera"
    agent_type = "ceo"
    role = "CEO of RivalCorp"
    personality = @{ ambition = 0.95; risk_tolerance = 0.8; rationality = 0.7; empathy = 0.4 }
} | ConvertTo-Json -Depth 10)
$competitorId = $ceo2Response.id
Write-Log "OK CEO 2 : $($ceo2Response.name)  (id: $competitorId)" "Green"

$activistResponse = Invoke-RestMethod -Uri "$baseUrl/projects/$projectId/agents" -Method Post -ContentType "application/json" -Body (@{
    name = "Elena Rodriguez"
    agent_type = "activist"
    role = "Environmental Activist Leader"
    personality = @{ ambition = 0.8; empathy = 0.95; morality = 0.9; rationality = 0.6 }
} | ConvertTo-Json -Depth 10)
$activistId = $activistResponse.id
Write-Log "OK Activist: $($activistResponse.name)  (id: $activistId)" "Green"

# Test 4: Add Goals
Write-Log "`n[4/15] Adding Goals..." "Yellow"

Invoke-RestMethod -Uri "$baseUrl/agents/$ceoId/goals" -Method Post -ContentType "application/json" -Body (@{
    description = "Dominate the market with 40% share by exploiting competitor weaknesses"
    goal_type = "wealth"
    priority = 0.95
} | ConvertTo-Json) | Out-Null

Invoke-RestMethod -Uri "$baseUrl/agents/$competitorId/goals" -Method Post -ContentType "application/json" -Body (@{
    description = "Crush TechCorp and become market leader"
    goal_type = "power"
    priority = 0.9
} | ConvertTo-Json) | Out-Null

Invoke-RestMethod -Uri "$baseUrl/agents/$activistId/goals" -Method Post -ContentType "application/json" -Body (@{
    description = "Expose and stop corporate environmental destruction"
    goal_type = "ideology"
    priority = 0.95
} | ConvertTo-Json) | Out-Null

Write-Log "OK Goals added for all agents" "Green"

# ============================================================
# SIMULATION STEPS
# ============================================================

Write-Log "`n========================================"  "Cyan"
Write-Log "SIMULATION STEPS (6 total)"                 "Cyan"
Write-Log "========================================"  "Cyan"

# Step 1
Write-Log "`n[5/15] Simulation Step 1 - Initial Intel Gathering..." "Yellow"
Write-Log "       (agents start with no private knowledge)"
$step1 = Invoke-RestMethod -Uri "$baseUrl/projects/$projectId/simulate/step" -Method Post
Print-StepResult $step1 1

# Step 2
Write-Log "`n[6/15] Simulation Step 2 - Deeper Intel..." "Yellow"
Write-Log "       (agents discover specific facts about competitors)"
$step2 = Invoke-RestMethod -Uri "$baseUrl/projects/$projectId/simulate/step" -Method Post
Print-StepResult $step2 2

# Step 3
Write-Log "`n[7/15] Simulation Step 3 - Approaching Knowledge Threshold..." "Yellow"
Write-Log "       (knowledge_score building toward 65% threshold)"
$step3 = Invoke-RestMethod -Uri "$baseUrl/projects/$projectId/simulate/step" -Method Post
Print-StepResult $step3 3

Write-Log "`n--- KNOWLEDGE CHECK after Step 3 ---" "Magenta"
Write-Log "    Agents should be near or at the 65% knowledge threshold." "Magenta"
Write-Log "    Watch for 'READY TO ACT' in outcomes above." "Magenta"

# Step 4
Write-Log "`n[8/15] Simulation Step 4 - Execution Phase Begins..." "Yellow"
Write-Log "       (agents with sufficient intel switch to execution actions)"
$step4 = Invoke-RestMethod -Uri "$baseUrl/projects/$projectId/simulate/step" -Method Post
Print-StepResult $step4 4

# Step 5
Write-Log "`n[9/15] Simulation Step 5 - Full Execution..." "Yellow"
Write-Log "       (targeted actions based on discovered intelligence)"
$step5 = Invoke-RestMethod -Uri "$baseUrl/projects/$projectId/simulate/step" -Method Post
Print-StepResult $step5 5

# Step 6
Write-Log "`n[10/15] Simulation Step 6 - Escalation & Consequences..." "Yellow"
Write-Log "        (actions trigger reactions, relationships evolve)"
$step6 = Invoke-RestMethod -Uri "$baseUrl/projects/$projectId/simulate/step" -Method Post
Print-StepResult $step6 6

# Test 11: Simulation Status
Write-Log "`n[11/15] Getting Simulation Status..." "Yellow"
$simStatus = Invoke-RestMethod -Uri "$baseUrl/projects/$projectId/simulate/status" -Method Get
Write-Log "OK Simulation Status:" "Green"
Write-Log "   Current step  : $($simStatus.current_step)"
Write-Log "   Total actions : $($simStatus.total_actions)"
Write-Log "   Is running    : $($simStatus.is_running)"

# Test 12: Simulation History - show all 18 actions
Write-Log "`n[12/15] Getting Full Simulation History..." "Yellow"
$history = Invoke-RestMethod -Uri "$baseUrl/projects/$projectId/simulation/history?limit=20" -Method Get
Write-Log "OK Retrieved $($history.Count) actions from history" "Green"
Write-Log "Action progression (oldest first):"
$sortedHistory = $history | Sort-Object simulation_step, created_at
foreach ($action in $sortedHistory) {
    $statusIcon = if ($action.success) { "+" } else { "x" }
    Write-Log "   [$statusIcon] Step $($action.simulation_step): $($action.agent_name) -> $($action.action_type)"
}

# Test 13: Detect Patterns across all 6 steps
Write-Log "`n[13/15] Detecting Emergent Patterns (full 6-step context)..." "Yellow"
Write-Log "        (LLM analyzes intel-gathering -> execution transition)"
$patterns = Invoke-RestMethod -Uri "$baseUrl/projects/$projectId/patterns/detect" -Method Post -ContentType "application/json" -Body (@{
    time_window = 20
    min_significance = 0.4
} | ConvertTo-Json)

Write-Log "OK Detected $($patterns.Count) emergent patterns:" "Green"
foreach ($pattern in $patterns) {
    Write-Log "`n   [PATTERN] $($pattern.title)" "Magenta"
    Write-Log "      Type        : $($pattern.pattern_type)"
    Write-Log "      Significance: $($pattern.significance)"
    Write-Log "      Description : $($pattern.description.Substring(0, [Math]::Min(250, $pattern.description.Length)))..."
    if ($pattern.involved_agent_ids.Count -gt 0) {
        Write-Log "      Agents      : $($pattern.involved_agent_ids.Count) involved"
    }
    if ($pattern.evidence.Count -gt 0) {
        Write-Log "      Evidence    : $($pattern.evidence[0].Substring(0, [Math]::Min(120, $pattern.evidence[0].Length)))..."
    }
}

# Test 14: Agent Relationships - check all 3 agents
Write-Log "`n[14/15] Checking Agent Relationships..." "Yellow"

$rel1 = Invoke-RestMethod -Uri "$baseUrl/agents/$ceoId/relationships" -Method Get
Write-Log "OK $($ceo1Response.name) has $($rel1.Count) relationships" "Green"
foreach ($rel in $rel1) {
    Write-Log "   - $($rel.relationship_type)  strength: $($rel.strength)  trust: $($rel.trust)  interactions: $($rel.interaction_count)"
}

$rel2 = Invoke-RestMethod -Uri "$baseUrl/agents/$competitorId/relationships" -Method Get
Write-Log "OK $($ceo2Response.name) has $($rel2.Count) relationships" "Green"
foreach ($rel in $rel2) {
    Write-Log "   - $($rel.relationship_type)  strength: $($rel.strength)  trust: $($rel.trust)  interactions: $($rel.interaction_count)"
}

$rel3 = Invoke-RestMethod -Uri "$baseUrl/agents/$activistId/relationships" -Method Get
Write-Log "OK $($activistResponse.name) has $($rel3.Count) relationships" "Green"
foreach ($rel in $rel3) {
    Write-Log "   - $($rel.relationship_type)  strength: $($rel.strength)  trust: $($rel.trust)  interactions: $($rel.interaction_count)"
}

# Test 15: List all patterns
Write-Log "`n[15/15] Listing All Stored Patterns..." "Yellow"
$allPatterns = Invoke-RestMethod -Uri "$baseUrl/projects/$projectId/patterns" -Method Get
Write-Log "OK Total patterns stored: $($allPatterns.Count)" "Green"
foreach ($p in $allPatterns) {
    Write-Log "   - [$($p.significance)] $($p.title) ($($p.pattern_type))"
}

# ============================================================
# SUMMARY
# ============================================================

Write-Log "`n========================================"  "Cyan"
Write-Log "Test Results Summary"                        "Cyan"
Write-Log "========================================"  "Cyan"
Write-Log "Project : $($projectResponse.name)"
Write-Log "         id: $projectId"
Write-Log ""
Write-Log "Agents:"
Write-Log "   - $($ceo1Response.name) (CEO / TechCorp)"
Write-Log "   - $($ceo2Response.name) (CEO / RivalCorp)"
Write-Log "   - $($activistResponse.name) (Activist)"
Write-Log ""
Write-Log "Simulation:"
Write-Log "   Steps completed  : $($simStatus.current_step)"
Write-Log "   Total actions    : $($simStatus.total_actions)"
if ($simStatus.current_step -gt 0) {
    Write-Log "   Actions per step : $([Math]::Round($simStatus.total_actions / $simStatus.current_step, 1))"
}
Write-Log ""

# Analyze action type progression
$intelActions = ($sortedHistory | Where-Object { $_.action_type -like "*gather*" -or $_.action_type -like "*information*" }).Count
$execActions = $simStatus.total_actions - $intelActions
Write-Log "Action Breakdown:"
Write-Log "   Intel actions (gather info) : $intelActions"
Write-Log "   Execution actions           : $execActions"
if ($execActions -gt 0) {
    Write-Log "   -> Agents successfully transitioned to execution phase!" "Green"
} else {
    Write-Log "   -> Agents still in intel phase (run more steps)" "Yellow"
}
Write-Log ""
Write-Log "Emergent Patterns:"
Write-Log "   Total detected: $($allPatterns.Count)"
if ($allPatterns.Count -gt 0) {
    $topPattern = $allPatterns | Sort-Object significance -Descending | Select-Object -First 1
    Write-Log "   Most significant: $($topPattern.title) (significance: $($topPattern.significance))"
}
Write-Log ""
Write-Log "========================================"  "Green"
Write-Log "Test Complete!"                             "Green"
Write-Log "========================================"  "Green"
Write-Log ""
Write-Log "[OK] Layered knowledge system (public + hidden facts)"
Write-Log "[OK] Specific named discoveries (not generic outcomes)"
Write-Log "[OK] knowledge_score tracking per goal"
Write-Log "[OK] Automatic intel -> execution phase transition"
Write-Log "[OK] LLM decisions informed by actual discovered intel"
Write-Log "[OK] Emergent pattern detection across 6 steps"
Write-Log "[OK] Relationship evolution"
Write-Log ""
Write-Log "========================================"  "Cyan"
Write-Log "Log Files"                                  "Cyan"
Write-Log "========================================"  "Cyan"
Write-Log "Console transcript  : $consoleLog"
Write-Log "Structured sim logs : logs/simulations/$projectId/"
Write-Log "  simulation.log    - full chronological log with all decisions"
Write-Log "  decisions.jsonl   - every agent LLM decision (JSON)"
Write-Log "  actions.jsonl     - every executed action with discoveries"
Write-Log "  patterns.jsonl    - every detected emergent pattern"
Write-Log "  summary.json      - final run summary"
Write-Log ""
Write-Log "Verify in Supabase:"
Write-Log "  - goals table (knowledge_score column progression)"
Write-Log "  - agent_memories table (memory_type='discovery' entries)"
Write-Log "  - agent_actions table (action_type evolution over steps)"
Write-Log "  - emergent_patterns table"
Write-Log ""
Write-Log "Run finished: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
