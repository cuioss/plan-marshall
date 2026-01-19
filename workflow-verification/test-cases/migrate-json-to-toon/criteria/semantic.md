# Semantic Verification Criteria: migrate-json-to-toon

## Overview

Verifies that the outline phase correctly identifies all marketplace components with JSON output specifications that should be migrated to TOON format.

## Scope Correctness

The workflow must analyze the correct scope:

- [ ] Analyzes **agents** (request says "agent/command/skill outputs")
- [ ] Analyzes **commands** (request says "agent/command/skill outputs")
- [ ] Analyzes **skills** (request says "agent/command/skill outputs")
- [ ] Scans **all bundles** (request doesn't specify bundles)
- [ ] Logs scope decision with `[DECISION]` tag

**Expected scope decision**:
```
[DECISION] Scope: resource-types=agents,commands,skills, bundles=all
  detail: Request explicitly mentions "agent/command/skill outputs" - scanning all three types
```

## Completeness

All expected items must be found:

### Agents (10 files)
- [ ] All 9 pm-dev-java agents identified
- [ ] 1 pm-plugin-development agent identified (tool-coverage-agent)

### Skills with JSON Output Specs (5 files)
- [ ] 2 plan-marshall skills identified (permission-doctor, permission-fix)
- [ ] 3 pm-dev-frontend skills identified (js-fix-jsdoc, js-generate-coverage, js-implement-tests)

### Commands (0 files)
- [ ] Correctly identifies NO commands have JSON output specs

**Expected count**: 15 affected files total

**Critical checks - Must be found**:

| File | Reason |
|------|--------|
| pm-dev-java/agents/java-implement-agent.md | "Step 3: Return Results" with ```json |
| pm-plugin-development/agents/tool-coverage-agent.md | "Output" with ```json |
| plan-marshall/skills/permission-doctor/SKILL.md | "Output JSON" sections (3 blocks) |
| plan-marshall/skills/permission-fix/SKILL.md | "Output (JSON)" sections (5+ blocks) |
| pm-dev-frontend/skills/js-fix-jsdoc/SKILL.md | "JSON Output Contract" section |
| pm-dev-frontend/skills/js-generate-coverage/SKILL.md | "Step 3: Return Coverage Results" with ```json |
| pm-dev-frontend/skills/js-implement-tests/SKILL.md | "JSON Output Contract" section |

## Exclusion Criteria

**Files that MUST NOT be included**:

### Agents excluded (use TOON or markdown output):
- `plan-marshall/agents/research-best-practices.md` - Uses markdown format (```), not JSON
- `pm-workflow/agents/plan-init-agent.md` - Uses TOON format (2 ```toon blocks)
- `pm-workflow/agents/task-plan-agent.md` - Uses TOON format
- `pm-workflow/agents/task-execute-agent.md` - Uses TOON format
- `pm-workflow/agents/solution-outline-agent.md` - Uses TOON format

### Commands excluded (JSON is not output spec):
- `pm-plugin-development/commands/tools-analyze-user-prompted.md` - JSON blocks are solution examples showing permission format

### Skills excluded (JSON is config/input, not output):
- `pm-dev-frontend/skills/js-enforce-eslint/SKILL.md` - JSON is "Required npm Scripts" (package.json config)
- `pm-dev-java/skills/java-enforce-logrecords/SKILL.md` - JSON is "Configuration structure" (input config)
- `pm-plugin-development/skills/plugin-create/SKILL.md` - JSON is "answers_json contains" (input format)

## Skills Inclusion/Exclusion Decision

**Key distinction for skills**:

| JSON Context | Include? |
|--------------|----------|
| "Output JSON", "JSON Output Contract", "Return...Results" | YES |
| "Configuration", "Required", "Input", "contains" | NO |

**Expected decision logs**:
```
[FINDING] Affected: plan-marshall/skills/permission-doctor/SKILL.md
  detail: Skill with "Output JSON" sections containing ```json output blocks

[FINDING] Excluded: pm-dev-frontend/skills/js-enforce-eslint/SKILL.md
  detail: JSON block is npm scripts configuration, not skill output specification
```

## Scoring Guidance

**90-100 (Excellent)**:
- All 15 files found (10 agents + 5 skills)
- All critical checks passed
- Inclusion/exclusion distinction documented with context analysis
- Non-JSON agent exclusions logged
- Config/input JSON exclusions logged

**70-89 (Good)**:
- 13-15 files found
- Minor documentation gaps
- Distinction mentioned but rationale brief

**50-69 (Partial)**:
- 10-12 files found
- Missing multiple skills OR multiple agents
- Exclusion decisions undocumented

**0-49 (Poor)**:
- Fewer than 10 files found
- Wrong scope (e.g., skills excluded entirely)
- No exclusion reasoning
