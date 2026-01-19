# Path-Multi Workflow

Workflow for cross-cutting changes that affect shared patterns, interfaces, or conventions across multiple components.

## Critical Requirement

Goals MUST contain explicit file paths. A goal that says "update all X" without listing the files is INVALID - it just restates the request.

## Step 3b.1: Load Marketplace Inventory

**CRITICAL**: Use the `scan-marketplace-inventory` script for component discovery. Do NOT use ad-hoc Glob/Grep for this purpose.

**Note**: Use `--trace-plan-id` for plan-scoped logging (the script doesn't have its own `--plan-id` parameter).

### Log Scope Decision

Before scanning, log the scope decision based on request analysis:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[DECISION] (pm-plugin-development:ext-outline-plugin) Scope: resource-types={types}, bundles={all|filtered}
  detail: {rationale from request analysis}"
```

### Execute Inventory Scan

```bash
# Full inventory with descriptions
python3 .plan/execute-script.py \
  pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --trace-plan-id {plan_id} \
  --include-descriptions

# Or filter by bundles if impact is known to be limited
python3 .plan/execute-script.py \
  pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --trace-plan-id {plan_id} \
  --bundles planning,pm-dev-java \
  --include-descriptions
```

### Link Inventory to References

After scan completes, record the scan parameters in references.toon:

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references set \
  --plan-id {plan_id} \
  --field inventory_scan \
  --value "{timestamp}:{resource-types}:{bundle-filter}"
```

## Step 3b.2: Analyze Each Component

### Batch Processing

Process components in batches of **10-15 files** per bundle. After each batch:

1. Log a checkpoint to work-log
2. Review findings before continuing
3. Do NOT skip components or rush through batches

```bash
# After each batch of 10-15 components
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[STATUS] (pm-plugin-development:ext-outline-plugin) Analyzed {component_type} batch {N} of {bundle}: {X} affected, {Y} not affected"
```

**All component types must have batch checkpoints** - if inventory includes agents, commands, AND skills, all three types must show batch progress logs.

### Per-Component Analysis

For each component, execute these steps **in order**:

1. **Read** the component file completely
2. **Search** for references to the changed entity
3. **Evaluate** against the checklist below
4. **Record** the result (affected or not, with reason)

**Analysis checklist per component**:
- [ ] Does it reference the changed skill/command/agent?
- [ ] Does it use the changed script notation?
- [ ] Does it follow the pattern being modified?
- [ ] Does it output in the format being changed?

### Checklist Enforcement Rules

**CRITICAL**: The analysis checklist MUST be applied to EVERY component returned by inventory scan.

1. **No blanket exclusions**: You CANNOT exclude an entire component type (agents, commands, skills) with a single decision. Each component must be analyzed individually.

2. **One [FINDING] per component**: Every component gets its own `[FINDING]` log entry - either "Affected" or "Not affected" with component-specific reasoning.

3. **No categorical assumptions**: Statements like "skills are knowledge documents" or "commands don't produce output" are PROHIBITED. Components must be evaluated against the REQUEST criteria, not component-type assumptions.

**Anti-pattern (INVALID):**
```
[FINDING] Skills analysis complete: Skills are knowledge documents without output formats
```

**Correct pattern:**
```
[FINDING] Affected: plan-marshall/skills/permission-doctor/SKILL.md
  detail: Contains "Output JSON" section matching request criteria

[FINDING] Not affected: pm-dev-java/skills/junit-core/SKILL.md
  detail: No output specification sections found after checking Output, Return, Contract sections
```

### Logging Affected Files

For each **affected** file, log immediately:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[FINDING] (pm-plugin-development:ext-outline-plugin) Affected: {file_path} - {reason}"
```

**Build affected files list** as you analyze:
```
affected_files:
  bundle-a:
    - path/to/file1.md (reason: uses JSON output)
    - path/to/file2.md (reason: references changed pattern)
  bundle-b:
    - path/to/file3.md (reason: produces affected format)
```

### Document Excluded Components

For files analyzed but NOT affected, log with rationale using `[FINDING]`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[FINDING] (pm-plugin-development:ext-outline-plugin) Not affected: {file}
  detail: {rationale}"
```

The rationale should explain WHY the component is not affected based on request analysis:
- What was the matching criteria from the request?
- Why did this file not meet the criteria?

Example patterns:
- `{file} matched discovery pattern but content analysis shows {criteria} not present`
- `{file} excluded: {element} is {category}, not {target_category}`

### Final Verification

After all batches complete, log the summary:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[MILESTONE] (pm-plugin-development:ext-outline-plugin) Impact analysis complete: {total_affected} of {total_analyzed} affected"
```

### Link Affected Files to References

After analysis complete, persist affected files for execute phase:

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references add-list \
  --plan-id {plan_id} \
  --field affected_files \
  --values "{comma-separated-paths}"
```

## Step 3b.3: Build Deliverables Section with Enumeration

**Deliverable Organization**: Create one deliverable per bundle (or per ~5-8 files if a bundle has many). Each deliverable MUST list the specific files to modify.

**Deliverable Requirements** (all fields mandatory for Path-Multi):

| Field | Description | Example |
|-------|-------------|---------|
| `files` | Explicit list of file paths | `marketplace/bundles/pm-workflow/agents/solution-outline-agent.md` |
| `change_per_file` | What changes in each file | "Replace ```json output blocks with ```toon" |
| `verification` | How to verify the change | "Grep for ```json returns 0 matches" |

### Deliverable Template

```markdown
### 1. Update {bundle} {component-type}s for {change}

**Metadata:**
- change_type: migrate
- execution_mode: automated
- domain: plan-marshall-plugin-dev
- profile: implementation
- depends: none

**Affected files:**
- `{path/to/file1.md}`
- `{path/to/file2.md}`
- `{path/to/file3.md}`

**Change per file:** {specific change description}

**Verification:**
- Command: `/pm-plugin-development:plugin-doctor --component {path}`
- Criteria: No quality issues detected

**Success Criteria:**
- {criterion 1}
- {criterion 2}
```

### Valid Example

```markdown
### 1. Update pm-workflow agents to TOON output

**Affected files:**
- `marketplace/bundles/pm-workflow/agents/plan-init-agent.md`
- `marketplace/bundles/pm-workflow/agents/solution-outline-agent.md`
- `marketplace/bundles/pm-workflow/agents/task-plan-agent.md`

**Change per file:** Replace output format from JSON to TOON in Return/Output sections
**Verification:** grep -l 'status: success' returns all files, grep -l '"status":' returns none

**Success Criteria:**
- All agents use TOON output format
- No JSON output blocks remain
```

### Anti-pattern (INVALID)

```markdown
### 1. Update agent output formats to TOON

Migrate all agent .md files to specify TOON output format
```
This restates the request without enumeration. The solution outline phase added no information.

## Decomposition Patterns

| Request Pattern | Typical Deliverables |
|-----------------|----------------------|
| "Rename notation X to Y" | 1. Update core definition 2-N. Update each referencing component |
| "Change output format" | 1. Define new format 2-N. Update each producer/consumer |
| "Migrate to new API" | 1. Implement new API 2-N. Migrate each caller |
