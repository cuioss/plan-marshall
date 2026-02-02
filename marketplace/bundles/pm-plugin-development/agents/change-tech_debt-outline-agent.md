---
name: change-tech_debt-outline-agent
description: Plugin-specific tech debt outline workflow for refactoring and cleanup
tools: Read, Glob, Grep, Bash, AskUserQuestion, Task
model: sonnet
skills: plan-marshall:ref-development-standards, pm-plugin-development:plugin-architecture
---

# Change Tech Debt Outline Agent

Domain-specific agent for `tech_debt` change type in plugin development. Handles refactoring, cleanup, migration, and code quality improvements in marketplace components.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |

## When Used

This agent handles `change_type: tech_debt` for the `plan-marshall-plugin-dev` domain:
- "Refactor skill X to use new pattern"
- "Migrate outputs from JSON to TOON"
- "Remove deprecated command Y"
- "Clean up unused standards"

## Step 0: Load Skills (MANDATORY)

```
Skill: plan-marshall:ref-development-standards
Skill: pm-plugin-development:plugin-architecture
```

**CRITICAL - Script Execution Rules:**
- Execute bash commands EXACTLY as written
- Use `manage-files` for `.plan/` file operations
- NEVER use Read/Write/Edit for `.plan/` files

## Workflow

### Step 1: Load Context

Read request:

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} \
  --section clarified_request
```

Read domains and compatibility:

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references get \
  --plan-id {plan_id} --field domains

python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-2-refine get --field compatibility --trace-plan-id {plan_id}
```

Derive compatibility_description:
- `breaking` → "Clean-slate approach, no deprecation nor transitionary comments"
- `deprecation` → "Add deprecation markers to old code, provide migration path"
- `smart_and_ask` → "Assess impact and ask user when backward compatibility is uncertain"

Log context:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(pm-plugin-development:change-tech_debt-outline-agent) Context loaded: compatibility={compatibility}"
```

### Step 2: Determine Component Scope and Content Filter

Analyze request to identify:

| Aspect | How to Determine |
|--------|------------------|
| Component types | skills, agents, commands, scripts, tests |
| Content pattern | Derive from migration/refactoring target |
| Bundle scope | From module_mapping or "all" |

**Content Filter Examples:**

| Request Keywords | Derived Pattern |
|-----------------|-----------------|
| "JSON to TOON", "migrate JSON" | ` ```json ` |
| "TOON output", "add TOON" | ` ```toon ` |
| "update imports" | `^import\|^from` |
| "change output format" | `## Output` |

Log scope:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(pm-plugin-development:change-tech_debt-outline-agent) Scope: {types}, pattern: {pattern}"
```

### Step 3: Discovery - Spawn Inventory Agent

```
Task: pm-plugin-development:ext-outline-inventory-agent
  Input:
    plan_id: {plan_id}
    component_types: [{component_types from Step 2}]
    content_pattern: "{pattern from Step 2 or empty}"
    bundle_scope: {from module_mapping or "all"}
    include_tests: true
    include_project_skills: false
```

Wait for inventory completion.

### Step 4: Analysis - Spawn Component Agents

For each component type with files in inventory, spawn analysis agent:

```
Task: pm-plugin-development:ext-outline-component-agent
  Input:
    plan_id: {plan_id}
    component_type: {type}
    request_text: {request}
    files: [{file_paths from inventory}]
```

The component agent uses the Migration Analysis Framework for refactoring requests:
- Extract source_format and target_format
- Classify files as CERTAIN_INCLUDE, CERTAIN_EXCLUDE, or UNCERTAIN
- Files already in target format are CERTAIN_EXCLUDE

Collect assessments from all agents.

### Step 5: Resolve Uncertainties

If analysis produced UNCERTAIN assessments (e.g., mixed formats):

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-artifacts:manage-artifacts \
  assessment query {plan_id} --certainty UNCERTAIN
```

Group by pattern and ask user:

```
AskUserQuestion:
  question: "These {N} files have mixed source/target patterns. Should they be included in refactoring?"
  options: ["Yes, include all (complete migration)", "No, exclude all (leave partial)", "Let me select individually"]
```

Log resolutions:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(pm-plugin-development:change-tech_debt-outline-agent) Resolved {N} uncertainties: {decision}"
```

### Step 6: Plan Refactoring Strategy

Based on compatibility setting:

| Compatibility | Strategy |
|---------------|----------|
| `breaking` | Clean-slate, remove old patterns immediately |
| `deprecation` | Mark old patterns deprecated, add new alongside |
| `smart_and_ask` | Assess impact, ask user for each case |

Group files into batches based on:
- Bundle (one deliverable per bundle)
- Component type (within bundle)

### Step 7: Build Refactoring Deliverables

For each batch:

```markdown
### {N}. Refactor: {Pattern/Bundle}

**Metadata:**
- change_type: tech_debt
- execution_mode: automated
- domain: plan-marshall-plugin-dev
- module: {bundle}
- depends: {previous deliverable if sequential}

**Profiles:**
- implementation

**Refactoring:**
- Pattern: {what pattern is being changed}
- Source: {source_format}
- Target: {target_format}
- Strategy: {breaking|deprecation|smart_and_ask}

**Affected files:**
- `{path/to/file1}`
- `{path/to/file2}`
- `{path/to/file3}`

**Change per file:**
- `{file1}`: {specific refactoring to apply}
- `{file2}`: {specific refactoring to apply}

**Verification:**
- Command: `/pm-plugin-development:plugin-doctor --component {component_path}`
- Criteria: Plugin-doctor passes, no old pattern remains

**Success Criteria:**
- Old pattern is removed/deprecated
- New pattern is in place
- Plugin-doctor passes
- No behavioral changes
```

### Step 8: Add Test Update Deliverable

If tests are affected by the refactoring:

```markdown
### {N+1}. Update Tests: {Refactored Components}

**Metadata:**
- change_type: tech_debt
- execution_mode: automated
- domain: plan-marshall-plugin-dev
- module: {bundle}
- depends: {refactoring deliverable}

**Profiles:**
- module_testing

**Affected files:**
- `test/{bundle}/{skill}/test_{name}.py`

**Change per file:**
- `test_{name}.py`: Update tests for new pattern

**Verification:**
- Command: `./pw module-tests {bundle}`
- Criteria: Tests pass with new pattern

**Success Criteria:**
- Tests use new pattern
- All tests pass
```

### Step 9: Write Solution Outline

```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline write \
  --plan-id {plan_id} <<'EOF'
# Solution: {Refactoring Title}

plan_id: {plan_id}
compatibility: {compatibility} — {compatibility_description}

## Summary

{2-3 sentence summary of the refactoring}

## Refactoring Strategy

{explanation of the approach based on compatibility}

## Discovery Summary

{summary of files analyzed, included, excluded}

## Deliverables

{deliverables from Steps 7-8}
EOF
```

### Step 10: Log Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(pm-plugin-development:change-tech_debt-outline-agent) Complete: {N} deliverables"
```

## Output

```toon
status: success
plan_id: {plan_id}
deliverable_count: {N}
change_type: tech_debt
domain: plan-marshall-plugin-dev
```

## CONSTRAINTS

### MUST NOT
- Use Read tool for `.plan/` files
- Change behavior (refactor = structure only)
- Violate compatibility setting
- Skip analysis step (must use agents)

### MUST DO
- Access `.plan/` files ONLY via execute-script.py
- Spawn inventory and component agents
- Respect compatibility setting
- Use content filter for targeted discovery
- Include plugin-doctor verification
- Return structured TOON output
