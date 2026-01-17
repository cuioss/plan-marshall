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

- [ ] All 9 pm-dev-java agents with JSON output specs are identified
- [ ] The 1 pm-plugin-development agent (tool-coverage-agent) is identified
- [ ] The 1 pm-dev-frontend command (js-generate-coverage) is identified
- [ ] Total: 11 affected files

**Expected count**: 11 affected files

**Critical check**: js-generate-coverage.md MUST be found
- Location: `marketplace/bundles/pm-dev-frontend/commands/js-generate-coverage.md`
- Reason: Contains "Step 3: Return Coverage Results" with ```json block

**Files that should NOT be included**:
- `pm-dev-java/commands/java-enforce-logrecords.md` - JSON is config structure, not output spec
- `pm-plugin-development/commands/tools-analyze-user-prompted.md` - JSON is permission format example

## Decision Quality

Decisions must have clear rationale:

- [ ] Skills exclusion decision is documented with rationale
- [ ] Exclusion reasons explain WHY skills don't have outputs (they document, don't execute)
- [ ] False positive exclusions (config examples vs output specs) are documented

**Expected skills decision**:
```
[DECISION] Skills excluded from deliverables
  detail: Skills document formats but don't have outputs themselves. JSON blocks in skills are:
  - Script output docs: Scripts already support TOON, skill docs are examples
  - API docs: External formats, not controllable
  - Schemas: Contract definitions must remain stable
  - Configs: External file formats, not outputs
```

**Expected exclusion logging for false positives**:
```
[FINDING] Not affected: pm-dev-java/commands/java-enforce-logrecords.md
  detail: JSON block is configuration structure example, not command output specification
```

## Scoring Guidance

**90-100 (Excellent)**:
- All 11 files found
- js-generate-coverage.md included
- Skills exclusion documented with clear rationale
- False positive exclusions logged

**70-89 (Good)**:
- 10-11 files found
- Minor documentation gaps
- Skills exclusion mentioned but rationale brief

**50-69 (Partial)**:
- 8-9 files found
- Missing js-generate-coverage.md OR multiple agents
- Exclusion decisions undocumented

**0-49 (Poor)**:
- Fewer than 8 files found
- Wrong scope (e.g., only agents analyzed)
- No exclusion reasoning
