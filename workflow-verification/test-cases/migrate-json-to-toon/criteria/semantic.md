# Semantic Verification Criteria: migrate-json-to-toon

## Overview

Verifies that the outline phase correctly identifies all plan-marshall components with JSON **stdout output** that should be migrated to TOON format. This includes both documentation (SKILL.md files) AND Python scripts.

**Key distinction**: Only scripts that use `print(json.dumps())` for stdout output are in scope. Scripts that write JSON to files (internal storage) are NOT in scope.

## Scope Correctness

The workflow must analyze the correct scope:

- [ ] Analyzes **agents** (request says "agents/commands/skills outputs")
- [ ] Analyzes **commands** (request says "agents/commands/skills outputs")
- [ ] Analyzes **skills** (request says "agents/commands/skills outputs")
- [ ] Analyzes **scripts** (clarification: "Both docs and scripts")
- [ ] Scans **plan-marshall bundle ONLY** (clarification: "plan-marshall only")
- [ ] Logs scope decision to `decision.log`

**Expected scope decision** (in decision.log):
```
(pm-plugin-development:ext-outline-plugin) Component scope: [skills, agents, commands, scripts, tests]
(pm-plugin-development:ext-outline-plugin) Context loaded: domains=[plan-marshall-plugin-dev], bundle=plan-marshall
```

## Completeness

All expected items must be found:

### Skills Documentation (3 files)
- [ ] workflow-integration-ci/SKILL.md identified
- [ ] workflow-integration-git/SKILL.md identified
- [ ] workflow-integration-sonar/SKILL.md identified

### Python Scripts (3 files)
- [ ] pr.py identified (has print(json.dumps()))
- [ ] git-workflow.py identified (has print(json.dumps()))
- [ ] sonar.py identified (has print(json.dumps()))

### Test Files (3 files)
- [ ] test_pr.py identified
- [ ] test_git_workflow.py identified
- [ ] test_sonar.py identified

### Agents and Commands (0 files)
- [ ] No plan-marshall agents/commands have JSON output specs that need migration

**Expected count**: 9 affected files total

**Note**: tools-planning-inventory was absorbed into pm-plugin-development:tools-marketplace-inventory and is no longer in the plan-marshall bundle scope.

**Critical checks - Must be found**:

| File | Reason |
|------|--------|
| plan-marshall/skills/workflow-integration-ci/SKILL.md | JSON output documentation |
| plan-marshall/skills/workflow-integration-ci/scripts/pr.py | print(json.dumps()) |

## Exclusion Criteria

**Files that MUST NOT be included**:

### Other bundles (OUT OF SCOPE per user clarification):
- `pm-dev-java/agents/*` - Wrong bundle
- `pm-plugin-development/agents/*` - Wrong bundle
- `plan-marshall/skills/*` - Wrong bundle

### plan-marshall agents (all use TOON already):
- `plan-marshall/agents/plan-init-agent.md` - Uses TOON format
- `plan-marshall/agents/task-plan-agent.md` - Uses TOON format
- `plan-marshall/agents/solution-outline-agent.md` - Uses TOON format
- `plan-marshall/agents/q-gate-validation-agent.md` - Uses TOON format

### plan-marshall scripts that write JSON to files (not stdout):
- `manage-plan-artifacts/scripts/artifact_store.py` - Uses f.write(json.dumps()), not print()
  - This writes to JSONL files for internal storage, not script output

### plan-marshall skills already using TOON output:
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
[PROGRESS] (pm-plugin-development:ext-outline-plugin) Inventory: 3-4 skills with JSON code blocks in plan-marshall
```

## Scoring Guidance

**90-100 (Excellent)**:
- All 9 files found (3 SKILL.md + 3 scripts + 3 tests)
- All critical checks passed
- Scope correctly limited to plan-marshall bundle
- Both docs and scripts included
- File-write JSON correctly excluded

**70-89 (Good)**:
- 7-9 files found
- Minor documentation gaps
- Scope correct but reasoning brief

**50-69 (Partial)**:
- 5-7 files found
- Missing some scripts OR docs
- May have included file-write JSON incorrectly

**0-49 (Poor)**:
- Fewer than 5 files found
- Wrong scope (e.g., all bundles included despite clarification)
- Scripts ignored despite clarification
- Included artifact_store.py (file write, not stdout)
