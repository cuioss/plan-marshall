# Semantic Verification Criteria: migrate-json-to-toon

## Overview

Verifies that the outline phase correctly identifies all pm-workflow components with JSON **stdout output** that should be migrated to TOON format. This includes both documentation (SKILL.md files) AND Python scripts.

**Key distinction**: Only scripts that use `print(json.dumps())` for stdout output are in scope. Scripts that write JSON to files (internal storage) are NOT in scope.

## Scope Correctness

The workflow must analyze the correct scope:

- [ ] Analyzes **agents** (request says "agents/commands/skills outputs")
- [ ] Analyzes **commands** (request says "agents/commands/skills outputs")
- [ ] Analyzes **skills** (request says "agents/commands/skills outputs")
- [ ] Analyzes **scripts** (clarification: "Both docs and scripts")
- [ ] Scans **pm-workflow bundle ONLY** (clarification: "pm-workflow only")
- [ ] Logs scope decision to `decision.log`

**Expected scope decision** (in decision.log):
```
(pm-plugin-development:ext-outline-plugin) Component scope: [skills, agents, commands, scripts, tests]
(pm-plugin-development:ext-outline-plugin) Context loaded: domains=[plan-marshall-plugin-dev], bundle=pm-workflow
```

## Completeness

All expected items must be found:

### Skills Documentation (4 files)
- [ ] planning-inventory/SKILL.md identified
- [ ] workflow-integration-ci/SKILL.md identified
- [ ] workflow-integration-git/SKILL.md identified
- [ ] workflow-integration-sonar/SKILL.md identified

### Python Scripts (4 files)
- [ ] scan-planning-inventory.py identified (has print(json.dumps()))
- [ ] pr.py identified (has print(json.dumps()))
- [ ] git-workflow.py identified (has print(json.dumps()))
- [ ] sonar.py identified (has print(json.dumps()))

### Test Files (4 files)
- [ ] test_scan_planning_inventory.py identified
- [ ] test_pr.py identified
- [ ] test_git_workflow.py identified
- [ ] test_sonar.py identified

### Agents and Commands (0 files)
- [ ] No pm-workflow agents/commands have JSON output specs that need migration

**Expected count**: 12 affected files total

**Critical checks - Must be found**:

| File | Reason |
|------|--------|
| pm-workflow/skills/planning-inventory/SKILL.md | JSON output documentation |
| pm-workflow/skills/planning-inventory/scripts/scan-planning-inventory.py | print(json.dumps()) |
| pm-workflow/skills/workflow-integration-ci/SKILL.md | JSON output documentation |
| pm-workflow/skills/workflow-integration-ci/scripts/pr.py | print(json.dumps()) |

## Exclusion Criteria

**Files that MUST NOT be included**:

### Other bundles (OUT OF SCOPE per user clarification):
- `pm-dev-java/agents/*` - Wrong bundle
- `pm-plugin-development/agents/*` - Wrong bundle
- `plan-marshall/skills/*` - Wrong bundle

### pm-workflow agents (all use TOON already):
- `pm-workflow/agents/plan-init-agent.md` - Uses TOON format
- `pm-workflow/agents/task-plan-agent.md` - Uses TOON format
- `pm-workflow/agents/solution-outline-agent.md` - Uses TOON format
- `pm-workflow/agents/q-gate-validation-agent.md` - Uses TOON format

### pm-workflow scripts that write JSON to files (not stdout):
- `manage-plan-artifacts/scripts/artifact_store.py` - Uses f.write(json.dumps()), not print()
  - This writes to JSONL files for internal storage, not script output

### pm-workflow skills already using TOON output:
- `manage-config/scripts/manage-config.py` - Outputs TOON
- `manage-tasks/scripts/manage-tasks.py` - Outputs TOON
- `manage-references/scripts/manage-references.py` - Outputs TOON
- `manage-solution-outline/scripts/manage_solution_outline.py` - Outputs TOON

## Script Discovery

**Key distinction for scripts**:

| Pattern | Include? | Reason |
|---------|----------|--------|
| `print(json.dumps())` | YES | Stdout output consumed by callers |
| `f.write(json.dumps())` | NO | File write for internal storage |
| `json.loads()` | NO | Input parsing only |

**Expected decision logs**:
```
[PROGRESS] (pm-plugin-development:ext-outline-plugin) Inventory: 4-5 skills with JSON code blocks in pm-workflow
```

## Scoring Guidance

**90-100 (Excellent)**:
- All 12 files found (4 SKILL.md + 4 scripts + 4 tests)
- All critical checks passed
- Scope correctly limited to pm-workflow bundle
- Both docs and scripts included
- File-write JSON correctly excluded

**70-89 (Good)**:
- 10-12 files found
- Minor documentation gaps
- Scope correct but reasoning brief

**50-69 (Partial)**:
- 8-10 files found
- Missing some scripts OR docs
- May have included file-write JSON incorrectly

**0-49 (Poor)**:
- Fewer than 8 files found
- Wrong scope (e.g., all bundles included despite clarification)
- Scripts ignored despite clarification
- Included artifact_store.py (file write, not stdout)
