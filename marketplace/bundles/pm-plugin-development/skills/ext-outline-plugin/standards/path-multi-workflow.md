# Path-Multi Workflow

Workflow for cross-cutting changes that affect shared patterns, interfaces, or conventions across multiple components.

## Step 1: Receive Scope from Assessment Protocol

The following are provided by Assessment Steps 1-3 and MUST be used:

| Input | Source | Description |
|-------|--------|-------------|
| `affected_artifacts` | Step 1.6 | Component types to scan (e.g., [Skills, Agents]) |
| `bundle_scope` | Step 2.3 | Bundles to scan (e.g., "all" or [pm-dev-java, pm-workflow]) |

**CRITICAL**: Do NOT re-derive scope. Use the values from Steps 1-2 directly to constrain:
1. The inventory scan parameters
2. Which components are analyzed

```
LOG: [STATUS] Using scope from initial analysis:
  affected_artifacts: {affected_artifacts}
  bundle_scope: {bundle_scope}
```

## Critical Requirement

Goals MUST contain explicit file paths. A goal that says "update all X" without listing the files is INVALID - it just restates the request.

## Step 2: Load Marketplace Inventory

**CRITICAL**: Use the `scan-marketplace-inventory` script for component discovery. Do NOT use ad-hoc Glob/Grep for this purpose.

**Note**: Use `--trace-plan-id` for plan-scoped logging (the script doesn't have its own `--plan-id` parameter).

### Use Step 1 Outputs for Scan Parameters

The inventory scan MUST use the pre-determined scope from Step 1:

```bash
# Build scan parameters from Step 1 outputs
resource_types = affected_artifacts  # From Step 1
bundles = bundle_scope               # From Step 1

LOG: [STATUS] Executing inventory scan with pre-determined scope:
  resource_types: {resource_types}
  bundles: {bundles}
```

**CRITICAL**: Do NOT re-derive scope here. Use the exact values from Step 1.

### Execute Inventory Scan

```bash
# Use affected_artifacts to filter resource types
# Use bundle_scope to filter bundles (use "all" if bundle_scope == "all")
python3 .plan/execute-script.py \
  pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --trace-plan-id {plan_id} \
  --resource-types {affected_artifacts}  # From Step 1
  --bundles {bundle_scope}               # From Step 1 (or omit if "all")
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

## Step 3: Extract Request Matching Criteria

**Purpose**: Before analyzing components, extract explicit criteria that define "what makes a component affected" based on the REQUEST text. These criteria constrain ALL subsequent per-component analysis.

**CRITICAL**: This step is MANDATORY. Skipping to Step 4 without completing this step is a workflow violation.

### Derive Criteria from Request

Analyze the request text to extract:

1. **Request fragment**: The specific phrase that defines the change scope
2. **Criteria statement**: What makes a component "affected" - in objective terms
3. **Match indicators**: Concrete patterns/elements that indicate a match
4. **Exclude indicators**: Patterns that explicitly exclude a component

```
ANALYZE request text:
  1. Identify the ACTION (migrate, rename, update, change)
  2. Identify the SUBJECT (what is being changed - format, notation, pattern)
  3. Identify the SCOPE (outputs, references, usages)

Derive:
  request_fragment = "{exact quote from request}"
  criteria = "{subject} in {scope} context"
  match_indicators = [concrete patterns that indicate match]
  exclude_indicators = [concrete patterns that indicate non-match]
```

### Log Matching Criteria

Before proceeding to component analysis, log the derived criteria:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[DECISION] (pm-plugin-development:ext-outline-plugin) Request Matching Criteria:
  request_fragment: \"{request_fragment}\"
  criteria: \"{criteria}\"
  match_indicators: {match_indicators}
  exclude_indicators: {exclude_indicators}"
```

### Criteria Quality Validation

The extracted criteria MUST be:

| Requirement | Valid | Invalid |
|-------------|-------|---------|
| **Derived from request** | "Has JSON output blocks" (from "migrate outputs from JSON") | "Is a knowledge document" (assumption) |
| **Objective** | "Contains ```json in Output section" | "Seems to use JSON" |
| **Testable** | grep pattern or section presence | Subjective judgment |

**Anti-patterns (PROHIBITED):**
```
criteria: "Component could be affected"     # Too vague
criteria: "Skills are documentation"        # Categorical assumption
criteria: "Outputs data"                    # Not derived from request
exclude_indicators: ["Skills", "Commands"]  # NEVER use component TYPES as exclude indicators
```

**CRITICAL**: Match and exclude indicators must describe CONTENT characteristics, never COMPONENT TYPES.

| WRONG (component type) | CORRECT (content characteristic) |
|------------------------|----------------------------------|
| `"Skills (knowledge documents)"` | `"JSON is configuration not output"` |
| `"Commands don't have outputs"` | `"No Output/Return section found"` |
| `"Agents already migrated"` | `"Already uses TOON format"` |

The criteria determine WHAT to look for. Step 4 applies those criteria to EACH component regardless of type. Component type filtering was already done in Step 1 (affected_artifacts).

### Persist Criteria for Analysis

After logging, the criteria become the **benchmark** for all Step 4 findings. Every `[FINDING]` log MUST reference these criteria.

## Step 4: Analyze Each Component (via Agent Delegation)

**Purpose**: Delegate component analysis to specialized agents that have structured output contracts. This enforces per-component analysis and prevents categorical assumptions.

**Contract**: See `standards/component-analysis-contract.md` for agent input/output specifications.

### Step 4.1: Group Components by Type

From inventory results, group files by component type:

```
skills_files = [paths from inventory where type == "skill"]
command_files = [paths from inventory where type == "command"]
agent_files = [paths from inventory where type == "agent"]
```

Log the grouping:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[STATUS] (pm-plugin-development:ext-outline-plugin) Component grouping:
  skills: {len(skills_files)} files
  commands: {len(command_files)} files
  agents: {len(agent_files)} files"
```

### Step 4.2: Spawn Analysis Agents (MANDATORY)

**CRITICAL**: You MUST use the **Task tool** to spawn analysis agents. Do NOT perform inline analysis. Do NOT skip agent spawning. The Task tool invocation is REQUIRED for each component type with files.

For each component type with files, invoke the Task tool with these parameters:

**Skills Analysis** (if skills_files not empty):

| Parameter | Value |
|-----------|-------|
| `description` | "Analyze skills batch {N}" |
| `subagent_type` | `pm-plugin-development:skill-analysis-agent` |
| `prompt` | See template below |

Prompt template:
```
Analyze skills against criteria.

file_paths:
  {list all skills_files in this batch, one per line}

criteria:
  request_fragment: "{request_fragment from Step 3}"
  criteria_statement: "{criteria from Step 3}"
  match_indicators: {match_indicators from Step 3}
  exclude_indicators: {exclude_indicators from Step 3}

batch_id: skills-{N}-{bundle}
plan_id: {plan_id}
```

**Commands Analysis** (if command_files not empty):

| Parameter | Value |
|-----------|-------|
| `description` | "Analyze commands batch {N}" |
| `subagent_type` | `pm-plugin-development:command-analysis-agent` |
| `prompt` | Same template structure with command_files |

**Agents Analysis** (if agent_files not empty):

| Parameter | Value |
|-----------|-------|
| `description` | "Analyze agents batch {N}" |
| `subagent_type` | `pm-plugin-development:agent-analysis-agent` |
| `prompt` | Same template structure with agent_files |

**Batching**: If a component type has more than 15 files, invoke multiple Task tools with batches of 10-15 files each. Run batches in parallel when possible.

**Verification**: After invoking Task tools, you will receive TOON-formatted results from each agent. Proceed to Step 4.3 to validate these results.

### Step 4.3: Validate Agent Results

For each agent response, validate the output contract:

1. **Completeness check**: `findings.length == file_paths.length`
2. **Evidence check**: Each finding has `evidence` populated
3. **Count check**: `affected_count + not_affected_count == total_analyzed`

**If validation fails**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} ERROR "[VALIDATION] (pm-plugin-development:ext-outline-plugin) Agent validation failed: {batch_id}
  expected_findings: {file_paths.length}
  actual_findings: {findings.length}
  action: Retry or escalate"
```

**If validation succeeds**, log batch checkpoint:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[STATUS] (pm-plugin-development:ext-outline-plugin) Analyzed {component_type} batch {N}: {affected_count} affected, {not_affected_count} not affected"
```

### Step 4.4: Aggregate Findings

Merge all agent findings into unified structure:

```
affected_files:
  bundle-a:
    - path/to/file1.md (criteria_match: {indicator} - {evidence})
    - path/to/file2.md (criteria_match: {indicator} - {evidence})
  bundle-b:
    - path/to/file3.md (criteria_match: {indicator} - {evidence})

analysis_summary:
  skills: {total} analyzed, {affected} affected
  commands: {total} analyzed, {affected} affected
  agents: {total} analyzed, {affected} affected
```

### Step 4.5: Final Verification

After all agents complete, log the milestone:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[MILESTONE] (pm-plugin-development:ext-outline-plugin) Impact analysis complete: {total_affected} of {total_analyzed} affected"
```

### Step 4.6: Link Affected Files to References

Persist affected files for execute phase:

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references add-list \
  --plan-id {plan_id} \
  --field affected_files \
  --values "{comma-separated-paths}"
```

## Step 5: Build Deliverables Section with Enumeration

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
