# Failure Categories

Root cause taxonomy for structural verification failures, adapted from `tools-analyze-script-failures`.

## Category Definitions

| Category | Description | Typical Indicators |
|----------|-------------|-------------------|
| **Missing Artifact** | Expected file or section doesn't exist | File not found, section absent |
| **Schema Violation** | Artifact exists but has invalid format | Parse errors, missing required fields |
| **Count Mismatch** | Expected count differs from actual | N expected vs M found |
| **Scope Mismatch** | Wrong components were analyzed | Missing or extra components |
| **Reference Mismatch** | Actual differs from golden reference | Content differs, structure differs |
| **Test Case Error** | Test definition is incorrect | Invalid test-id, malformed criteria |

## Origin Tracing Guidance

For each failure category, trace backwards through the component chain to identify the origin.

### Missing Artifact

**Trace to**: Component responsible for creating the artifact.

| Artifact | Likely Origin |
|----------|---------------|
| `solution_outline.md` | `manage-solution-outline` skill/script |
| `config.toon` | `phase-1-init` or `manage-config` |
| `TASK-*.toon` | `phase-3-plan` or `manage-tasks` |
| `references.toon` | `manage-references` skill/script |

### Schema Violation

**Trace to**: Component that writes the artifact.

Common violations:
- Missing required TOON fields
- Invalid Markdown structure
- Malformed list syntax in TOON arrays

### Count Mismatch

**Trace to**: Component that determines scope or iteration logic.

Check:
- Was the correct scope passed to the component?
- Did the component iterate over all expected items?
- Are filter conditions too restrictive?

### Scope Mismatch

**Trace to**: Component that selects or filters components for analysis.

Check:
- Module detection logic in `phase-2-outline`
- Domain filtering in `config.toon`
- Component selection criteria

### Reference Mismatch

**Trace to**: Component that generates the differing content.

Compare:
- Expected structure vs actual structure
- Expected values vs actual values
- Expected formatting vs actual formatting

### Test Case Error

**Trace to**: Test case definition files.

Check:
- `test-definition.toon` syntax and values
- `expected-artifacts.toon` accuracy
- `criteria/*.md` validity

## Fix Direction by Category

| Category | Fix Direction |
|----------|---------------|
| Missing Artifact | Ensure component is invoked; check component logic |
| Schema Violation | Fix component output format; update schema expectations |
| Count Mismatch | Adjust scope logic or update test expectations |
| Scope Mismatch | Fix component selection; verify config settings |
| Reference Mismatch | Update golden reference or fix component output |
| Test Case Error | Correct test case definition files |

## Confidence Levels

When attributing failures to components, assign confidence levels:

| Confidence | Criteria |
|------------|----------|
| **High** | Direct causal chain visible; single possible origin |
| **Medium** | Likely origin based on responsibility; other possibilities exist |
| **Low** | Multiple possible origins; requires investigation |
