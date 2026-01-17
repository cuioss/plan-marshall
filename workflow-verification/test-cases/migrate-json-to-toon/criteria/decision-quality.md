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

## Skills Exclusion Decision

**Expected**: Skills excluded from deliverables despite being scanned

**Rationale must address**:
1. Skills are knowledge documents, not executors
2. JSON blocks in skills represent documentation, not outputs
3. Types of JSON in skills:
   - Script output documentation
   - External API response examples
   - Schema/contract definitions
   - Configuration examples

**Impact if missing**:
- If skills are included: Scope score penalty (wrong boundary)
- If exclusion has no rationale: Quality score penalty

## Component Type Identification

**Expected pattern for identifying affected components**:

For agents:
- Look for "Return Results" or "Output" sections
- Check for ```json blocks following those sections
- Verify the JSON represents agent output specification

For commands:
- Look for "Return" or "Output" sections
- Check for ```json blocks
- Verify JSON is command output, not config example

**Decision trail should show**:
```
[FINDING] Affected: {path}
  detail: "{section name}" section contains ```json output block
```

## False Positive Handling

**Expected**: Explicit logging of non-affected files that might look affected

**Must document exclusions for**:
- `java-enforce-logrecords.md` - has JSON but it's config structure
- `tools-analyze-user-prompted.md` - has JSON but it's permission format

**Format**:
```
[FINDING] Not affected: {path}
  detail: {reason this JSON block is not an output specification}
```

## Deliverable Grouping Decision

**Expected**: Group by module, not individual files

**Rationale**:
- 9 pm-dev-java agents → 1 deliverable
- 1 pm-plugin-development agent → 1 deliverable
- 1 pm-dev-frontend command → 1 deliverable

**Total**: 3 deliverables covering 11 files

**Acceptable variations**:
- May split pm-dev-java further if justified
- May combine if clearly documented

**NOT acceptable**:
- 11 separate deliverables (one per file)
- Combining across domains without rationale
