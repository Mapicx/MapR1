# Quick Test Reference

## Restart Server First!
```powershell
# Stop current server (Ctrl+C in server terminal)
python main.py
```

Wait for: `Database tables created successfully`

---

## Run Tests

### Test Everything (Recommended)
```powershell
.\test_phase22.ps1
```
**Tests:** Entities, Relationships, Timelines, Scenarios
**Time:** ~2 minutes

---

### Individual Tests

**Entities Only:**
```powershell
.\test_entities.ps1
```
**Time:** ~10 seconds

**Timelines Only:**
```powershell
.\test_timelines.ps1
```
**Time:** ~2 minutes (includes scenario generation)

**Phase 2.1 (Persistence):**
```powershell
.\test_simple.ps1
```
**Time:** ~2 minutes

---

## What Gets Tested

### Phase 2.2 Full Test (`test_phase22.ps1`)
1. ✅ Create project
2. ✅ Create 3 entities (nation, company, person)
3. ✅ Create 2 relationships
4. ✅ Generate 2 scenarios with LLM
5. ✅ Create main timeline
6. ✅ Add scenarios to timeline
7. ✅ Create timeline branch
8. ✅ Get project summary

### Expected Output
```
╔════════════════════════════════════════╗
║  MapR1 Phase 2.2 - Full System Test  ║
╚════════════════════════════════════════╝

[1/8] Creating Project...
      ✓ Project created: Phase 2.2 Complete Test

[2/8] Creating Entities...
      ✓ Created 3 entities

[3/8] Creating Relationships...
      ✓ Created 2 relationships

[4/8] Generating Scenarios (1-2 minutes)...
      ✓ Generated 2 scenarios

[5/8] Creating Main Timeline...
      ✓ Timeline created: Prime Timeline

[6/8] Adding Scenarios to Timeline...
      ✓ Added 2 scenarios to timeline

[7/8] Creating Timeline Branch...
      ✓ Branch created: Alternate Reality - Quantum Failure
      ✓ Copied 2 scenarios

[8/8] Getting Project Summary...

╔════════════════════════════════════════╗
║         Test Results Summary          ║
╚════════════════════════════════════════╝

Project: Phase 2.2 Complete Test
  └─ Scenarios: 2
  └─ Entities: 3
     ├─ Nations: 1
     ├─ Companies: 1
     └─ People: 1
  └─ Relationships: 2
  └─ Timelines: 2
     ├─ Main: 1
     └─ Branches: 1

╔════════════════════════════════════════╗
║    ✓ All Phase 2.2 Tests Passed!     ║
╚════════════════════════════════════════╝
```

---

## Verify in Supabase

1. Go to: https://ygtzasxbpizkupixmgcg.supabase.co
2. Click **Table Editor**
3. Check these tables:

**Phase 2.1 Tables:**
- `projects` - Your test projects
- `scenarios` - Generated scenarios
- `timeline_events` - Events in scenarios

**Phase 2.2 Tables (NEW):**
- `entities` - Nations, people, companies, factions
- `relationships` - Connections between entities
- `timelines` - Main and branched timelines
- `timeline_scenarios` - Scenarios in each timeline

---

## Troubleshooting

### "Unable to connect to remote server"
→ Server not running. Run: `python main.py`

### "Table does not exist"
→ Server needs restart to create new tables

### "Timeout" during scenario generation
→ Normal! Takes 1-2 minutes. Script has 180s timeout.

### Import errors
→ Make sure virtual environment is activated:
```powershell
.\.venv\Scripts\Activate.ps1
```

---

## API Documentation

Once server is running:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## What's Implemented

✅ **Phase 1:** Scenario generation with LLM
✅ **Phase 2.1:** Database persistence (Supabase)
✅ **Phase 2.2:** Entities, Relationships, Timeline Branching

**Total API Endpoints:** 30+
**Total Database Tables:** 7

---

## Quick Commands

```powershell
# Start server
python main.py

# Run full test
.\test_phase22.ps1

# Test entities only
.\test_entities.ps1

# Test timelines only
.\test_timelines.ps1

# Test Phase 2.1 only
.\test_simple.ps1
```

---

**Ready!** Restart server and run `.\test_phase22.ps1` 🚀
