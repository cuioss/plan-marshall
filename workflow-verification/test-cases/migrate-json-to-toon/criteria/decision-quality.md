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

### Agents:
- `plan-marshall/agents/research-best-practices.md` - uses markdown format output
- `pm-workflow/agents/*` - already use TOON format (4 agents)

### Commands:
- `pm-plugin-development/commands/tools-analyze-user-prompted.md` - JSON is solution examples

### Skills with config/input JSON:
- `pm-dev-frontend/skills/js-enforce-eslint/SKILL.md` - JSON is npm scripts config
- `pm-dev-java/skills/java-enforce-logrecords/SKILL.md` - JSON is configuration structure
- `pm-plugin-development/skills/plugin-create/SKILL.md` - JSON is input format

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

**Total**: 4 deliverables covering 15 files

**Acceptable variations**:
- May split pm-dev-java further if justified
- May combine skills across bundles if clearly documented
- May separate permission-doctor and permission-fix if rationale provided

**NOT acceptable**:
- 15 separate deliverables (one per file)
- Combining agents and skills in same deliverable
- Including skills with config/input JSON
