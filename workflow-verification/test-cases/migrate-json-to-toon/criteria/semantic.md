# Semantic Verification Criteria: migrate-json-to-toon

## Overview

Verifies that the outline phase correctly identifies all marketplace components with JSON output specifications that should be migrated to TOON format.

## Scope Correctness

The workflow must analyze the correct scope:

- [ ] Analyzes **agents** (request says "agent/command/skill outputs")
- [ ] Analyzes **commands** (request says "agent/command/skill outputs")
- [ ] Analyzes **skills** (request says "agent/command/skill outputs")
- [ ] Scans **all bundles** (request doesn't specify bundles)
- [ ] Logs scope decision to `decision.log`

**Expected scope decision** (in decision.log):
```
(pm-plugin-development:ext-outline-plugin) Scope: resource-types=agents,commands,skills, bundles=all
  detail: Request explicitly mentions "agent/command/skill outputs" - scanning all three types
```

## Completeness

All expected items must be found:

### Agents (10 files)
- [ ] All 9 pm-dev-java agents identified
- [ ] 1 pm-plugin-development agent identified (tool-coverage-agent)

### Commands (0 files)
- [ ] tools-analyze-user-prompted.md correctly EXCLUDED (JSON is solution examples, not output)

### Skills with JSON Output Specs (8 files)
- [ ] 2 plan-marshall skills identified (permission-doctor, permission-fix)
- [ ] 3 pm-dev-frontend skills identified (js-fix-jsdoc, js-generate-coverage, js-implement-tests)
- [ ] 3 pm-documents skills identified (manage-adr, manage-interface, ref-documentation)

**Expected count**: 18 affected files total

**Critical checks - Must be found**:

| File | Reason |
|------|--------|
| pm-dev-java/agents/java-implement-agent.md | "Step 3: Return Results" with ```json |
| pm-plugin-development/agents/tool-coverage-agent.md | "Output" with ```json |
| plan-marshall/skills/permission-doctor/SKILL.md | "Output JSON" sections (3 blocks) |
| plan-marshall/skills/permission-fix/SKILL.md | "Output (JSON)" sections (5+ blocks) |
| pm-dev-frontend/skills/js-fix-jsdoc/SKILL.md | "JSON Output Contract" section |
| pm-dev-frontend/skills/js-generate-coverage/SKILL.md | "Step 3: Return Coverage Results" with ```json |
| pm-documents/skills/manage-adr/SKILL.md | "### Output" section with ```json |
| pm-documents/skills/manage-interface/SKILL.md | "### Output" section with ```json |
| pm-documents/skills/ref-documentation/SKILL.md | "Step 4: Parse JSON Output" with ```json |

## Exclusion Criteria

**Files that MUST NOT be included**:

### Agents excluded (use TOON or markdown output):
- `plan-marshall/agents/research-best-practices.md` - Uses markdown format (```), not JSON
- `pm-plugin-development/agents/inventory-assessment-agent.md` - Output section uses ```toon (line 296)
- `pm-workflow/agents/plan-init-agent.md` - Uses TOON format (2 ```toon blocks)
- `pm-workflow/agents/task-plan-agent.md` - Uses TOON format
- `pm-workflow/agents/task-execute-agent.md` - Uses TOON format
- `pm-workflow/agents/solution-outline-agent.md` - Uses TOON format

### Commands excluded (JSON is solution examples, not output):
- `pm-plugin-development/commands/tools-analyze-user-prompted.md` - JSON blocks show permission format examples in solutions, not command output specification

### Skills excluded (no JSON blocks at all):
- `pm-dev-frontend/skills/ext-triage-js/SKILL.md` - Knowledge-only skill, no JSON
- `pm-dev-frontend/skills/js-enforce-eslint/SKILL.md` - Reference skill, no JSON
- `pm-documents/skills/ext-triage-docs/SKILL.md` - Knowledge-only skill, no JSON
- `pm-dev-java/skills/ext-triage-java/SKILL.md` - Knowledge-only skill, no JSON
- `pm-dev-java/skills/java-enforce-logrecords/SKILL.md` - No JSON blocks
- `pm-requirements/skills/ext-triage-reqs/SKILL.md` - Knowledge-only skill, no JSON

### Skills excluded (JSON is config/documentation, not output):
- `pm-plugin-development/skills/ext-triage-plugin/SKILL.md` - JSON is Extension Registration config
- `pm-dev-java/skills/manage-maven-profiles/SKILL.md` - JSON is storage schema documentation

## Skills Inclusion/Exclusion Decision

**Key distinction for skills**:

| JSON Context | Include? |
|--------------|----------|
| "Output JSON", "JSON Output Contract", "Return...Results" | YES |
| "Configuration", "Required", "Input", "contains" | NO |
| Extension Registration / Storage schema | NO |
| No JSON blocks at all | NO |

**Expected decision logs**:
```
[FINDING] Affected: plan-marshall/skills/permission-doctor/SKILL.md
  detail: Skill with "Output JSON" sections containing ```json output blocks

[FINDING] Excluded: pm-dev-frontend/skills/js-enforce-eslint/SKILL.md
  detail: No JSON blocks found in file - nothing to migrate

[FINDING] Excluded: pm-plugin-development/skills/ext-triage-plugin/SKILL.md
  detail: JSON block is Extension Registration config, not skill output
```

## Scoring Guidance

**90-100 (Excellent)**:
- 17-18 files found (allowing minor variance)
- All critical checks passed
- Inclusion/exclusion distinction documented with context analysis
- TOON-format components excluded
- Solution example JSON exclusions logged

**70-89 (Good)**:
- 14-17 files found
- Minor documentation gaps
- Distinction mentioned but rationale brief

**50-69 (Partial)**:
- 10-14 files found
- Missing multiple skills OR multiple agents
- Exclusion decisions undocumented

**0-49 (Poor)**:
- Fewer than 10 files found
- Wrong scope (e.g., skills excluded entirely)
- No exclusion reasoning
- Files with TOON output included as false positives
