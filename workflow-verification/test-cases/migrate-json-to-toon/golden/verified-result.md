# Verified Assessment Result

**Task**: "Migrate agents / commands / skills outputs from JSON to TOON format for token efficiency"

**Scope Clarifications** (from user during refine phase):
- Output type: "Both docs and scripts"
- Bundles in scope: "plan-marshall only"
- Script migration: "Yes - full migration"

This is the EXPECTED correct assessment that the outline phase should produce.

---

## Correct Scope Analysis

**Request Analysis:**
- "agents/commands/skills outputs" → All three component types
- "JSON to TOON format" → Find JSON **stdout** output specifications
- User clarified "plan-marshall only" → Single bundle scope
- User clarified "both docs and scripts" → Include Python scripts

**Key Distinction:**
- `print(json.dumps())` = script OUTPUT (in scope)
- `f.write(json.dumps())` = internal file storage (NOT in scope)

**Scope Decision** (in decision.log):
```
(pm-plugin-development:ext-outline-plugin) Component scope: [skills, agents, commands, scripts, tests]
(pm-plugin-development:ext-outline-plugin) Context loaded: domains=[plan-marshall-plugin-dev], bundle=plan-marshall
```

---

## Discovery Results

**Inventory Scan:**
Uses `scan-marketplace-inventory` with content filter for ```json patterns.

**Script Discovery:**
```bash
grep -r "print.*json.dumps" marketplace/bundles/plan-marshall/skills/*/scripts/*.py
```

Results:
- `tools-marketplace-inventory/scripts/scan-planning-inventory.py` - print(json.dumps())
- `workflow-integration-ci/scripts/pr.py` - print(json.dumps())
- `workflow-integration-git/scripts/git-workflow.py` - print(json.dumps())
- `workflow-integration-sonar/scripts/sonar.py` - print(json.dumps())

---

## Agents with JSON Output Specs (0 files)

All plan-marshall agents already use TOON format.

---

## Commands with JSON Output Specs (0 files)

No plan-marshall commands have JSON output specifications.

---

## Skills Documentation with JSON Output Specs (4 files)

| File | Reason |
|------|--------|
| pm-plugin-development/skills/tools-marketplace-inventory/SKILL.md | ```json output blocks |
| plan-marshall/skills/workflow-integration-ci/SKILL.md | ```json output blocks |
| plan-marshall/skills/workflow-integration-git/SKILL.md | ```json output blocks |
| plan-marshall/skills/workflow-integration-sonar/SKILL.md | ```json output blocks |

---

## Python Scripts with print(json.dumps()) Output (4 files)

| File | Reason |
|------|--------|
| pm-plugin-development/skills/tools-marketplace-inventory/scripts/scan-planning-inventory.py | print(json.dumps()) |
| plan-marshall/skills/workflow-integration-ci/scripts/pr.py | print(json.dumps()) |
| plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py | print(json.dumps()) |
| plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py | print(json.dumps()) |

---

## Test Files (4 files)

| File | Reason |
|------|--------|
| test/pm-plugin-development/tools-marketplace-inventory/test_scan_planning_inventory.py | Tests for scan-planning-inventory.py |
| test/plan-marshall/workflow-integration-ci/test_pr.py | Tests for pr.py |
| test/plan-marshall/workflow-integration-git/test_git_workflow.py | Tests for git-workflow.py |
| test/plan-marshall/workflow-integration-sonar/test_sonar.py | Tests for sonar.py |

---

## Out of Scope - Exclusion Required

**Scripts with f.write(json.dumps()) - file writes, not stdout:**
```
artifact_store.py - writes JSON to JSONL files for internal storage (NOT script output)
```

**plan-marshall skills already using TOON output:**
```
manage-config/scripts/manage-config.py - Outputs TOON
manage-tasks/scripts/manage-tasks.py - Outputs TOON
manage-references/scripts/manage-references.py - Outputs TOON
manage-solution-outline/scripts/manage_solution_outline.py - Outputs TOON
```

**Other bundles excluded per user clarification:**
- pm-dev-java/* - Wrong bundle
- pm-plugin-development/* - Wrong bundle
- plan-marshall/* - Wrong bundle

---

## Expected Deliverables

**Preferred grouping**: 4 deliverables, one per skill (each includes SKILL.md + script + test)

**Deliverable 1**: Migrate tools-marketplace-inventory outputs to TOON
- Files: SKILL.md, scan-planning-inventory.py, test_scan_planning_inventory.py
- Domain: plan-marshall-plugin-dev
- Module: plan-marshall
- Profiles: implementation, testing

**Deliverable 2**: Migrate workflow-integration-ci outputs to TOON
- Files: SKILL.md, pr.py, test_pr.py
- Domain: plan-marshall-plugin-dev
- Module: plan-marshall
- Profiles: implementation, testing

**Deliverable 3**: Migrate workflow-integration-git outputs to TOON
- Files: SKILL.md, git-workflow.py, test_git_workflow.py
- Domain: plan-marshall-plugin-dev
- Module: plan-marshall
- Profiles: implementation, testing

**Deliverable 4**: Migrate workflow-integration-sonar outputs to TOON
- Files: SKILL.md, sonar.py, test_sonar.py
- Domain: plan-marshall-plugin-dev
- Module: plan-marshall
- Profiles: implementation, testing

**Alternative grouping** (also acceptable):
- 3 deliverables: all docs, all scripts, all tests

---

## Expected References.toon

```toon
track: complex
scope_estimate: few_files
module_mapping: plan-marshall

affected_files[12]:
  # Skills documentation (4)
  marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/SKILL.md
  marketplace/bundles/plan-marshall/skills/workflow-integration-ci/SKILL.md
  marketplace/bundles/plan-marshall/skills/workflow-integration-git/SKILL.md
  marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/SKILL.md
  # Python scripts (4)
  marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/scan-planning-inventory.py
  marketplace/bundles/plan-marshall/skills/workflow-integration-ci/scripts/pr.py
  marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py
  marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py
  # Test files (4)
  test/pm-plugin-development/tools-marketplace-inventory/test_scan_planning_inventory.py
  test/plan-marshall/workflow-integration-ci/test_pr.py
  test/plan-marshall/workflow-integration-git/test_git_workflow.py
  test/plan-marshall/workflow-integration-sonar/test_sonar.py
```

---

## Expected Log Entries

### decision.log Entries

```
(plan-marshall:phase-2-refine) Track: complex - migration pattern requires discovery
(pm-plugin-development:ext-outline-plugin) Component scope: [skills, agents, commands, scripts, tests]
(pm-plugin-development:ext-outline-plugin) Context loaded: domains=[plan-marshall-plugin-dev], bundle=plan-marshall
(pm-plugin-development:ext-outline-plugin) Change type: migrate
(pm-plugin-development:ext-outline-plugin) Complete: 4 deliverables, 8 affected files, 4 test files
```

### work.log Entries

```
[REFINE:6] (plan-marshall:phase-2-refine) Confidence: 64%. Threshold: 95%. Issues: Completeness, Ambiguity
[REFINE:8] (plan-marshall:phase-2-refine) Updated request with 3 clarifications
[REFINE:6] (plan-marshall:phase-2-refine) Confidence: 100%. Threshold: 95%. All issues resolved.
[PROGRESS] (pm-plugin-development:ext-outline-plugin) Inventory: 4-5 skills with JSON code blocks in plan-marshall
[ARTIFACT] (pm-plugin-development:ext-outline-plugin) Created solution_outline.md - 4 deliverables
```
