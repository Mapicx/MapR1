# Test Entities System
Write-Host "`n=== Testing Entities System ===" -ForegroundColor Cyan

$baseUrl = "http://localhost:8000"

# 1. Create a project first
Write-Host "`n1. Creating Project..." -ForegroundColor Yellow
$projectBody = @{
    name = "Entity Test Project"
    description = "Testing entities and relationships"
} | ConvertTo-Json

$project = Invoke-RestMethod -Uri "$baseUrl/api/projects" -Method Post -ContentType "application/json" -Body $projectBody
$projectId = $project.id
Write-Host "   Project ID: $projectId" -ForegroundColor Green

# 2. Create entities
Write-Host "`n2. Creating Entities..." -ForegroundColor Yellow

# Nation
$nationBody = @{
    type = "nation"
    name = "United Earth Federation"
    description = "A unified global government"
    attributes = @{
        population = 8000000000
        gdp = 150000000000000
        military_strength = "high"
    }
} | ConvertTo-Json

$nation = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/entities" -Method Post -ContentType "application/json" -Body $nationBody
Write-Host "   Created Nation: $($nation.name)" -ForegroundColor Green
$nationId = $nation.id

# Person
$personBody = @{
    type = "person"
    name = "Dr. Sarah Chen"
    description = "Lead scientist in fusion energy"
    attributes = @{
        age = 45
        role = "Chief Scientist"
        expertise = "Nuclear Fusion"
    }
} | ConvertTo-Json

$person = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/entities" -Method Post -ContentType "application/json" -Body $personBody
Write-Host "   Created Person: $($person.name)" -ForegroundColor Green
$personId = $person.id

# Company
$companyBody = @{
    type = "company"
    name = "FusionTech Industries"
    description = "Leading fusion energy company"
    attributes = @{
        founded = 2025
        employees = 50000
        revenue = 25000000000
    }
} | ConvertTo-Json

$company = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/entities" -Method Post -ContentType "application/json" -Body $companyBody
Write-Host "   Created Company: $($company.name)" -ForegroundColor Green
$companyId = $company.id

# 3. List all entities
Write-Host "`n3. Listing All Entities..." -ForegroundColor Yellow
$entities = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/entities"
Write-Host "   Total entities: $($entities.Count)" -ForegroundColor Green
foreach ($e in $entities) {
    Write-Host "   - $($e.name) ($($e.type))" -ForegroundColor Gray
}

# 4. Create relationships
Write-Host "`n4. Creating Relationships..." -ForegroundColor Yellow

# Person works for Company
$rel1Body = @{
    entity_a_id = $personId
    entity_b_id = $companyId
    relationship_type = "alliance"
    strength = "strong"
    description = "Dr. Chen works for FusionTech"
} | ConvertTo-Json

$rel1 = Invoke-RestMethod -Uri "$baseUrl/api/relationships?project_id=$projectId" -Method Post -ContentType "application/json" -Body $rel1Body
Write-Host "   Created: Person <-> Company (alliance)" -ForegroundColor Green

# Company partners with Nation
$rel2Body = @{
    entity_a_id = $companyId
    entity_b_id = $nationId
    relationship_type = "trade_partner"
    strength = "strong"
    description = "FusionTech supplies energy to UEF"
} | ConvertTo-Json

$rel2 = Invoke-RestMethod -Uri "$baseUrl/api/relationships?project_id=$projectId" -Method Post -ContentType "application/json" -Body $rel2Body
Write-Host "   Created: Company <-> Nation (trade_partner)" -ForegroundColor Green

# 5. List relationships
Write-Host "`n5. Listing Relationships..." -ForegroundColor Yellow
$relationships = Invoke-RestMethod -Uri "$baseUrl/api/projects/$projectId/relationships"
Write-Host "   Total relationships: $($relationships.Count)" -ForegroundColor Green
foreach ($r in $relationships) {
    Write-Host "   - $($r.relationship_type) ($($r.strength))" -ForegroundColor Gray
}

# 6. Update entity
Write-Host "`n6. Updating Entity..." -ForegroundColor Yellow
$updateBody = @{
    description = "Updated: Lead scientist and Nobel Prize winner"
    attributes = @{
        age = 46
        role = "Chief Scientist"
        expertise = "Nuclear Fusion"
        awards = @("Nobel Prize", "Fields Medal")
    }
} | ConvertTo-Json

$updated = Invoke-RestMethod -Uri "$baseUrl/api/entities/$personId" -Method Put -ContentType "application/json" -Body $updateBody
Write-Host "   Updated: $($updated.name)" -ForegroundColor Green

# 7. Get single entity
Write-Host "`n7. Getting Entity Details..." -ForegroundColor Yellow
$entity = Invoke-RestMethod -Uri "$baseUrl/api/entities/$personId"
Write-Host "   Name: $($entity.name)" -ForegroundColor Green
Write-Host "   Type: $($entity.type)" -ForegroundColor Green
Write-Host "   Description: $($entity.description)" -ForegroundColor Green

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Entities System Tests Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nProject ID: $projectId" -ForegroundColor Gray
Write-Host "Check Supabase for entities and relationships tables`n" -ForegroundColor Gray
