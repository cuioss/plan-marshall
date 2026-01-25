# Verified Assessment Result

**Task**: "Migrate agents / commands / skills outputs from JSON to TOON format for token efficiency"

**Scope Clarifications** (from user during refine phase):
- Output type: "Both docs and scripts"
- Bundles in scope: "pm-workflow only"
- Script migration: "Yes - full migration"

This is the EXPECTED correct assessment that the outline phase should produce.

---

## Correct Scope Analysis

**Request Analysis:**
- "agents/commands/skills outputs" → All three component types
- "JSON to TOON format" → Find JSON **stdout** output specifications
- User clarified "pm-workflow only" → Single bundle scope
- User clarified "both docs and scripts" → Include Python scripts

**Key Distinction:**
- `print(json.dumps())` = script OUTPUT (in scope)
- `f.write(json.dumps())` = internal file storage (NOT in scope)

**Scope Decision** (in decision.log):
```
(pm-plugin-development:ext-outline-plugin) Component scope: [skills, agents, commands, scripts, tests]
(pm-plugin-development:ext-outline-plugin) Context loaded: domains=[plan-marshall-plugin-dev], bundle=pm-workflow
```

---

## Discovery Results

**Inventory Scan:**
Uses `scan-marketplace-inventory` with content filter for ```json patterns.

**Script Discovery:**
```bash
grep -r "print.*json.dumps" marketplace/bundles/pm-workflow/skills/*/scripts/*.py
```

Results:
- `planning-inventory/scripts/scan-planning-inventory.py` - print(json.dumps())
- `workflow-integration-ci/scripts/pr.py` - print(json.dumps())
- `workflow-integration-git/scripts/git-workflow.py` - print(json.dumps())
- `workflow-integration-sonar/scripts/sonar.py` - print(json.dumps())

---

## Agents with JSON Output Specs (0 files)

All pm-workflow agents already use TOON format.

---

## Commands with JSON Output Specs (0 files)

No pm-workflow commands have JSON output specifications.

---

## Skills Documentation with JSON Output Specs (4 files)

| File | Reason |
|------|--------|
| pm-workflow/skills/planning-inventory/SKILL.md | ```json output blocks |
| pm-workflow/skills/workflow-integration-ci/SKILL.md | ```json output blocks |
| pm-workflow/skills/workflow-integration-git/SKILL.md | ```json output blocks |
| pm-workflow/skills/workflow-integration-sonar/SKILL.md | ```json output blocks |

---

## Python Scripts with print(json.dumps()) Output (4 files)

| File | Reason |
|------|--------|
| pm-workflow/skills/planning-inventory/scripts/scan-planning-inventory.py | print(json.dumps()) |
| pm-workflow/skills/workflow-integration-ci/scripts/pr.py | print(json.dumps()) |
| pm-workflow/skills/workflow-integration-git/scripts/git-workflow.py | print(json.dumps()) |
| pm-workflow/skills/workflow-integration-sonar/scripts/sonar.py | print(json.dumps()) |

---

## Test Files (4 files)

| File | Reason |
|------|--------|
| test/pm-workflow/planning-inventory/test_scan_planning_inventory.py | Tests for scan-planning-inventory.py |
| test/pm-workflow/workflow-integration-ci/test_pr.py | Tests for pr.py |
| test/pm-workflow/workflow-integration-git/test_git_workflow.py | Tests for git-workflow.py |
| test/pm-workflow/workflow-integration-sonar/test_sonar.py | Tests for sonar.py |

---

## Out of Scope - Exclusion Required

**Scripts with f.write(json.dumps()) - file writes, not stdout:**
```
artifact_store.py - writes JSON to JSONL files for internal storage (NOT script output)
```

**pm-workflow skills already using TOON output:**
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

**Deliverable 1**: Migrate planning-inventory outputs to TOON
- Files: SKILL.md, scan-planning-inventory.py, test_scan_planning_inventory.py
- Domain: plan-marshall-plugin-dev
- Module: pm-workflow
- Profiles: implementation, testing

**Deliverable 2**: Migrate workflow-integration-ci outputs to TOON
- Files: SKILL.md, pr.py, test_pr.py
- Domain: plan-marshall-plugin-dev
- Module: pm-workflow
- Profiles: implementation, testing

**Deliverable 3**: Migrate workflow-integration-git outputs to TOON
- Files: SKILL.md, git-workflow.py, test_git_workflow.py
- Domain: plan-marshall-plugin-dev
- Module: pm-workflow
- Profiles: implementation, testing

**Deliverable 4**: Migrate workflow-integration-sonar outputs to TOON
- Files: SKILL.md, sonar.py, test_sonar.py
- Domain: plan-marshall-plugin-dev
- Module: pm-workflow
- Profiles: implementation, testing

**Alternative grouping** (also acceptable):
- 3 deliverables: all docs, all scripts, all tests

---

## Expected References.toon

```toon
track: complex
scope_estimate: few_files
module_mapping: pm-workflow

affected_files[12]:
  # Skills documentation (4)
  marketplace/bundles/pm-workflow/skills/planning-inventory/SKILL.md
  marketplace/bundles/pm-workflow/skills/workflow-integration-ci/SKILL.md
  marketplace/bundles/pm-workflow/skills/workflow-integration-git/SKILL.md
  marketplace/bundles/pm-workflow/skills/workflow-integration-sonar/SKILL.md
  # Python scripts (4)
  marketplace/bundles/pm-workflow/skills/planning-inventory/scripts/scan-planning-inventory.py
  marketplace/bundles/pm-workflow/skills/workflow-integration-ci/scripts/pr.py
  marketplace/bundles/pm-workflow/skills/workflow-integration-git/scripts/git-workflow.py
  marketplace/bundles/pm-workflow/skills/workflow-integration-sonar/scripts/sonar.py
  # Test files (4)
  test/pm-workflow/planning-inventory/test_scan_planning_inventory.py
  test/pm-workflow/workflow-integration-ci/test_pr.py
  test/pm-workflow/workflow-integration-git/test_git_workflow.py
  test/pm-workflow/workflow-integration-sonar/test_sonar.py
```

---

## Expected Log Entries

### decision.log Entries

```
(pm-workflow:phase-2-refine) Track: complex - migration pattern requires discovery
(pm-plugin-development:ext-outline-plugin) Component scope: [skills, agents, commands, scripts, tests]
(pm-plugin-development:ext-outline-plugin) Context loaded: domains=[plan-marshall-plugin-dev], bundle=pm-workflow
(pm-plugin-development:ext-outline-plugin) Change type: migrate
(pm-plugin-development:ext-outline-plugin) Complete: 4 deliverables, 8 affected files, 4 test files
```

### work.log Entries

```
[REFINE:6] (pm-workflow:phase-2-refine) Confidence: 64%. Threshold: 95%. Issues: Completeness, Ambiguity
[REFINE:8] (pm-workflow:phase-2-refine) Updated request with 3 clarifications
[REFINE:6] (pm-workflow:phase-2-refine) Confidence: 100%. Threshold: 95%. All issues resolved.
[PROGRESS] (pm-plugin-development:ext-outline-plugin) Inventory: 4-5 skills with JSON code blocks in pm-workflow
[ARTIFACT] (pm-plugin-development:ext-outline-plugin) Created solution_outline.md - 4 deliverables
```
