# Decision Quality Criteria: migrate-json-to-toon

## Scope Decision

**Expected**: Analyze agents, commands, AND skills across all bundles

**Rationale should explain**:
- Request explicitly mentions all three component types
- No bundle restriction in request
- Scope determination based on request analysis

**Acceptable variations**:
- May mention "token efficiency" as goal context
- May note marketplace-wide scope

**NOT acceptable**:
- Analyzing only agents
- Limiting to specific bundles without justification

## Skills Inclusion/Exclusion Decision

**Expected**: Distinguish between skills with output specs vs config/input JSON

**Key distinction**:

| JSON Context | Include? |
|--------------|----------|
| "Output JSON", "JSON Output Contract", "Return...Results" | YES |
| "Configuration", "Required", "Input", "contains" | NO |

**Rationale must address**:
1. Skills with output specs have JSON blocks that represent actual output
2. Skills with config/input JSON are documenting inputs or configuration, not outputs

**Impact if missing**:
- If all skills excluded: Completeness penalty (missed 5 skills with output specs)
- If config/input skills included: Scope penalty (wrong distinction)
- If distinction has no rationale: Quality score penalty

## Component Type Identification

**Expected pattern for identifying affected components**:

For agents:
- Look for "Return Results" or "Output" sections
- Check for ```json blocks following those sections
- Verify the JSON represents agent output specification
- Exclude agents that use TOON or markdown format

For commands:
- Look for "Return" or "Output" sections
- Check for ```json blocks
- Verify JSON is command output, not solution example
- Note: Current codebase has no commands with JSON output specs

For skills:
- Look for "Output JSON", "JSON Output Contract", "Return...Results" sections with ```json blocks
- Exclude if JSON is "Configuration", "Required", "contains", "Input" context
- Include if skill has actual output specification

**Decision trail should show**:

In decision.log:
```
({component}) Scope: ...
  detail: ...
```

In work.log:
```
[FINDING] Affected: {path}
  detail: "{section name}" section contains ```json output block

[FINDING] Excluded: {path}
  detail: JSON block is {configuration/input format}, not output specification
```

## False Positive Handling

**Expected**: Explicit logging of non-affected files that might look affected

**Must document exclusions for**:

### Agents with TOON output (not JSON):
- `plan-marshall/agents/research-best-practices.md` - uses markdown format output
- `pm-plugin-development/agents/inventory-assessment-agent.md` - Output section uses ```toon
- `pm-workflow/agents/*` - already use TOON format (4 agents)

### Commands with solution-example JSON (not output specs):
- `pm-plugin-development/commands/tools-analyze-user-prompted.md` - JSON shows permission format in solution steps

### Skills with config/input JSON (not output specs):
- `pm-dev-frontend/skills/js-enforce-eslint/SKILL.md` - no JSON blocks at all
- `pm-dev-java/skills/java-enforce-logrecords/SKILL.md` - no JSON blocks at all
- `pm-plugin-development/skills/plugin-create/SKILL.md` - already uses TOON format
- `pm-plugin-development/skills/plugin-task-plan/SKILL.md` - already uses TOON format

**Format** (in work.log):
```
[FINDING] Not affected: {path}
  detail: {reason this JSON block is not an output specification}
```

## Deliverable Grouping Decision

**Expected**: Group by module, not individual files

**Rationale**:
- 9 pm-dev-java agents → 1 deliverable
- 1 pm-plugin-development agent → 1 deliverable
- 2 plan-marshall skills → 1 deliverable
- 3 pm-dev-frontend skills → 1 deliverable
- 3 pm-documents skills → 1 deliverable

**Total**: 5 deliverables covering 18 files

**Acceptable variations**:
- May split pm-dev-java further if justified (max 2 deliverables)
- May combine plan-marshall and pm-dev-frontend skills if same change pattern
- Total deliverables in range 4-6

**NOT acceptable**:
- 18 separate deliverables (one per file)
- Combining agents and skills in same deliverable
- Including TOON-format components (inventory-assessment-agent)
- Including solution-example JSON (tools-analyze-user-prompted)
