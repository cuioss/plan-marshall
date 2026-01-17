# Verified Assessment Result

**Task**: "Migrate agent/command/skill outputs from JSON to TOON format for token efficiency"

This is the EXPECTED correct assessment that the improved ext-outline-plugin should produce.

---

## Correct Scope Analysis

**Request Analysis:**
- "agent/command/skill outputs" → All three component types
- "JSON to TOON format" → Find JSON output specifications
- "token efficiency" → Goal, not constraint

**Scope Decision:**
```
[DECISION] (pm-plugin-development:ext-outline-plugin) Scope: resource-types=agents,commands,skills, bundles=all
  detail: Request explicitly mentions "agent/command/skill outputs" - scanning all three types
```

---

## Discovery Results

**Inventory Scan Parameters:**
```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --resource-types agents,commands,skills --include-descriptions --format json
```

**Reference:**
```
inventory_scan: 2026-01-17T08:53:20Z:agents,commands,skills:all
```

---

## Agents with JSON Output Specs (10 files)

All correctly identified:

| File | Reason |
|------|--------|
| pm-dev-java/agents/java-implement-agent.md | "Step 3: Return Results" with ```json |
| pm-dev-java/agents/java-implement-tests-agent.md | "Return Results" with ```json |
| pm-dev-java/agents/java-refactor-agent.md | "Return Results" with ```json |
| pm-dev-java/agents/java-coverage-agent.md | "Output" with ```json |
| pm-dev-java/agents/java-quality-agent.md | "Output" with ```json |
| pm-dev-java/agents/java-verify-agent.md | "Output" with ```json |
| pm-dev-java/agents/java-fix-build-agent.md | "Return Results" with ```json |
| pm-dev-java/agents/java-fix-tests-agent.md | "Return Results" with ```json |
| pm-dev-java/agents/java-fix-javadoc-agent.md | "Return Results" with ```json |
| pm-plugin-development/agents/tool-coverage-agent.md | "Output" with ```json |

---

## Commands with JSON Output Specs (1 file)

**MISSED by original assessment:**

| File | Reason |
|------|--------|
| pm-dev-frontend/commands/js-generate-coverage.md | "Step 3: Return Coverage Results" with ```json |

**Exclusion Log Required:**
```
[FINDING] (pm-plugin-development:ext-outline-plugin) Not affected: pm-dev-java/commands/java-enforce-logrecords.md
  detail: JSON block is configuration structure example, not command output specification

[FINDING] (pm-plugin-development:ext-outline-plugin) Not affected: pm-plugin-development/commands/tools-analyze-user-prompted.md
  detail: JSON blocks are permission file format examples, not command output specification
```

---

## Skills with JSON Blocks - Scope Decision

**Critical Decision Point**: Skills are knowledge documents, not executors. JSON blocks in skills represent:

1. **Script output documentation** - The skill documents what a SCRIPT returns
2. **External API response examples** - Documentation of third-party responses
3. **Schema/contract definitions** - Format specifications
4. **Configuration examples** - File format documentation

**Decision:**
```
[DECISION] (pm-plugin-development:ext-outline-plugin) Skills excluded from deliverables
  detail: Skills document formats but don't have outputs themselves. JSON blocks in skills are:
  - Script output docs: Scripts already support TOON, skill docs are examples
  - API docs: External formats, not controllable
  - Schemas: Contract definitions must remain stable
  - Configs: External file formats, not outputs
```

**Rationale**: Converting skill JSON documentation to TOON would:
- Break reference documentation (external APIs return JSON)
- Create inconsistency (script returns JSON, but docs show TOON)
- Require coordinated script changes (out of scope)

If script outputs should change, that's a separate task with broader scope.

---

## Expected Deliverables

**Deliverable 1**: Migrate pm-dev-java agents to TOON output format
- Files: 9 agents
- Domain: plan-marshall-plugin-dev
- Module: pm-dev-java

**Deliverable 2**: Migrate pm-plugin-development agent to TOON output format
- Files: 1 agent (tool-coverage-agent)
- Domain: plan-marshall-plugin-dev
- Module: pm-plugin-development

**Deliverable 3**: Migrate js-generate-coverage command to TOON output format
- Files: 1 command
- Domain: plan-marshall-plugin-dev
- Module: pm-dev-frontend

---

## Expected References.toon

```toon
inventory_scan: 2026-01-17T08:53:20Z:agents,commands,skills:all
affected_files[11]:
  marketplace/bundles/pm-dev-java/agents/java-implement-agent.md
  marketplace/bundles/pm-dev-java/agents/java-implement-tests-agent.md
  marketplace/bundles/pm-dev-java/agents/java-refactor-agent.md
  marketplace/bundles/pm-dev-java/agents/java-coverage-agent.md
  marketplace/bundles/pm-dev-java/agents/java-quality-agent.md
  marketplace/bundles/pm-dev-java/agents/java-verify-agent.md
  marketplace/bundles/pm-dev-java/agents/java-fix-build-agent.md
  marketplace/bundles/pm-dev-java/agents/java-fix-tests-agent.md
  marketplace/bundles/pm-dev-java/agents/java-fix-javadoc-agent.md
  marketplace/bundles/pm-plugin-development/agents/tool-coverage-agent.md
  marketplace/bundles/pm-dev-frontend/commands/js-generate-coverage.md
```

---

## Expected Work.log Entries

```
[DECISION] (pm-plugin-development:ext-outline-plugin) Path-Multi selected: cross-bundle impact, 3 modules affected
[DECISION] (pm-plugin-development:ext-outline-plugin) Scope: resource-types=agents,commands,skills, bundles=all
  detail: Request explicitly mentions "agent/command/skill outputs"
[STATUS] (pm-plugin-development:ext-outline-plugin) Scanning marketplace inventory
[FINDING] (pm-plugin-development:ext-outline-plugin) Affected: pm-dev-java/agents/java-implement-agent.md
  detail: "Step 3: Return Results" section contains ```json output block
[FINDING] ... (9 more agent entries)
[FINDING] (pm-plugin-development:ext-outline-plugin) Affected: pm-dev-frontend/commands/js-generate-coverage.md
  detail: "Step 3: Return Coverage Results" section contains ```json output block
[FINDING] (pm-plugin-development:ext-outline-plugin) Not affected: pm-dev-java/commands/java-enforce-logrecords.md
  detail: JSON block is configuration structure, not command output
[FINDING] (pm-plugin-development:ext-outline-plugin) Not affected: pm-plugin-development/commands/tools-analyze-user-prompted.md
  detail: JSON blocks are permission examples, not command output
[DECISION] (pm-plugin-development:ext-outline-plugin) Skills excluded from deliverables
  detail: Skills document formats but don't have outputs themselves
[MILESTONE] (pm-plugin-development:ext-outline-plugin) Impact analysis complete: 11 of 93 components affected
[ARTIFACT] (pm-plugin-development:ext-outline-plugin) Created solution_outline.md with 3 deliverables
```
