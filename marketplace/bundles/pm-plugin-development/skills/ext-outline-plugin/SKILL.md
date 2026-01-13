---
name: ext-outline-plugin
description: Analyze plugin codebase and create solution outline with deliverables
allowed-tools: Read, Glob, Grep, Bash
---

# Plugin Solution Outline Skill

**Role**: Domain analysis skill for plugin development tasks. Transforms the request into a solution document by analyzing the marketplace structure.

**Key Pattern**: Single solution document - deliverables are consolidated into `solution_outline.md` via `manage-solution-outline` skill.

## Contract Compliance

**MANDATORY**: All deliverables MUST follow the structure defined in the central contracts:

| Contract | Location | Purpose |
|----------|----------|---------|
| Deliverable Contract | `pm-workflow:manage-solution-outline/standards/deliverable-contract.md` | Required deliverable structure |
| Outline Extension Contract | `pm-workflow:workflow-extension-api/standards/extensions/outline-extension.md` | Outline extension pattern |

**Non-compliant deliverables will be rejected by validation.**

Every deliverable you create MUST have these sections in this exact order:

1. `### N. {Title}` - Numbered heading with action verb
2. `**Metadata:**` block with all 7 required fields
3. `**Affected files:**` with explicit file paths (no wildcards, no "all X")
4. `**Change per file:**` description of what changes
5. `**Verification:**` with command and criteria
6. `**Success Criteria:**` bullet list of measurable outcomes

## Required Skills

Load these skills at the start of any decomposition operation:

```
Skill: pm-plugin-development:plugin-architecture
Skill: pm-plugin-development:plugin-script-architecture
```

These provide:
- Architecture principles for marketplace components
- Script development patterns and testing standards
- Goal-based organization guidance

## Standards Documents

| Document | Purpose | Load When |
|----------|---------|-----------|
| [standards/path-single-workflow.md](standards/path-single-workflow.md) | Workflow for isolated 1-3 component changes | Path-Single determined |
| [standards/path-multi-workflow.md](standards/path-multi-workflow.md) | Workflow for cross-cutting changes | Path-Multi determined |
| [standards/reference-tables.md](standards/reference-tables.md) | Inventory script, skill mapping, component types, error handling | Always (reference) |
| [standards/script-verification.md](standards/script-verification.md) | Test creation, execution, organization validation | **Only when scripts affected** |

---

## Operation: decompose

**Input**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |

**Process**:

### Step 0: Load Solution Outline Skill

Load the solution outline skill for structure and examples:

```
Skill: pm-workflow:manage-solution-outline
```

This provides:
- Required document structure (Summary, Overview, Deliverables)
- ASCII diagram patterns for plugin integration tasks
- Deliverable reference format
- Realistic examples (see `examples/plugin-feature.md`)

### Step 1: Load Request Context

Load plan context via manage-* scripts:

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents \
  request read \
  --plan-id {plan_id}

python3 .plan/execute-script.py pm-workflow:manage-config:manage-config read \
  --plan-id {plan_id}

python3 .plan/execute-script.py pm-workflow:manage-references:manage-references read \
  --plan-id {plan_id}
```

Parse the request to identify what needs to be accomplished.

### Step 2: Determine Impact Path

Analyze the request to determine the impact scope:

**Path-Single** (Isolated Change):
- Creating/modifying 1-3 components in a single bundle
- No cross-references or dependencies to update
- Examples: "Add new skill", "Fix command X", "Create agent Y"

**Path-Multi** (Cross-Cutting Change):
- Changes affect shared patterns, interfaces, or conventions
- Multiple components reference the changed entity
- Examples: "Rename script notation", "Change output format", "Update API contract"

**Decision Criteria**:

| Indicator | Path |
|-----------|------|
| "add", "create", "new" (single component) | Single |
| "fix", "update" (localized) | Single |
| "rename", "migrate", "refactor" | Multi |
| "change format", "update pattern" | Multi |
| Cross-bundle impact mentioned | Multi |

**Log the decision**:

```bash
python3 .plan/execute-script.py plan-marshall:logging:manage-log \
  work {plan_id} INFO "[DECISION] (pm-plugin-development:ext-outline-plugin) Impact path: {Single|Multi} - {reasoning}"
```

---

### Step 3a: Path-Single Workflow

For isolated changes, follow [standards/path-single-workflow.md](standards/path-single-workflow.md).

**Key Points**:
1. Identify target bundle and component type
2. Read existing component (if modify/refactor scope)
3. Build deliverables section using the template

**Continue to Step 3c after building deliverables.**

---

### Step 3b: Path-Multi Workflow

For cross-cutting changes, follow [standards/path-multi-workflow.md](standards/path-multi-workflow.md).

**Key Points**:
1. Load marketplace inventory using `scan-marketplace-inventory`
2. Analyze components in batches of 10-15 files
3. Build explicit file enumeration for each deliverable

**CRITICAL**: Goals must contain explicit file paths. A goal that says "update all X" without listing the files is INVALID.

**Continue to Step 3c after building deliverables.**

---

### Step 3c: Create Solution Document

After building the deliverables section (from either Path-Single or Path-Multi workflow), write the solution document using heredoc. Validation is automatic on every write.

**Step 3c.1**: Write the solution document:

```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline \
  write \
  --plan-id {plan_id} <<'EOF'
# Solution Outline

## Summary
{One paragraph summary describing the solution approach}

## Overview
{ASCII diagram showing component relationships - see manage-solution-outline skill for patterns}

## Deliverables

### 1. {Action Verb} {Component Type}: {Name/Scope}

**Metadata:**
- change_type: {create|modify|refactor|migrate|delete}
- execution_mode: {automated|manual|mixed}
- domain: plan-marshall-plugin-dev
- profile: {implementation|testing}
- depends: none

**Affected files:**
- `marketplace/bundles/{bundle}/{type}/{file1}.md`
- `marketplace/bundles/{bundle}/{type}/{file2}.md`

**Change per file:** {Specific description of what changes in each file}

**Pattern:** (optional, for format changes)
```{format}
{pattern to apply}
```

**Verification:**
- Command: `/pm-plugin-development:plugin-doctor --component {path}`
- Criteria: No quality issues detected

**Success Criteria:**
- {Specific measurable criterion 1}
- {Specific measurable criterion 2}

### 2. {Next Deliverable Title}
{Same structure as above}
EOF
```

**Step 3c.2**: Check validation result.

The write command validates automatically. If validation fails, you will see errors like:

```toon
status: error
message: Deliverable contract violations detected
errors[N]:
- D1: Missing **Metadata:** block
- D2: Missing metadata field: suggested_skill
- D3: Wildcard in affected files: marketplace/bundles/*/agents/*.md
```

**If validation fails**: Fix the issues in your deliverables and re-run the write command. Do NOT proceed with invalid deliverables.

**Validation checks performed**:
- Every deliverable has `**Metadata:**` block
- Every metadata block has all 7 fields (change_type, execution_mode, domain, suggested_skill, suggested_workflow, context_skills, depends)
- Every deliverable has `**Affected files:**` with explicit paths
- No wildcards (`*`) or vague references ("all X") in affected files
- Every deliverable has `**Verification:**` section
- Every deliverable has `**Success Criteria:**` section

**Why heredoc?** Solution outlines contain ASCII diagrams and rich content that don't fit CLI parameter passing.

---

### Step 4: Record Issues as Lessons

On unexpected structure or ambiguity:

```bash
python3 .plan/execute-script.py plan-marshall:lessons-learned:manage-lesson add \
  --component-type skill \
  --component-name plugin-solution-outline \
  --category observation \
  --title "{issue summary}" \
  --detail "{context and resolution approach}"
```

### Step 5: Return Results

**Output**:
```toon
status: success
plan_id: {plan_id}
solution_created: true
impact_path: {Single|Multi}

deliverables_count: {number of deliverables in solution document}
total_files_affected: {sum of files across all deliverables}
components_analyzed: {count for Path-Multi, 0 for Path-Single}
lessons_recorded: {count}
```

**Path-Multi Validation**: If `total_files_affected` is 0 or deliverables don't contain file paths, the decomposition is incomplete.

---

## Verification Requirements

### Generic Component Verification

For each deliverable that creates or updates a component (skill, command, agent), the deliverable MUST include verification using the `/plugin-doctor` command:

```markdown
**Verification:**
- Command: `/pm-plugin-development:plugin-doctor --component {component_path}`
- Criteria: No quality issues detected
```

**Component paths format**:
- Skills: `marketplace/bundles/{bundle}/skills/{skill-name}/SKILL.md`
- Commands: `marketplace/bundles/{bundle}/commands/{command-name}.md`
- Agents: `marketplace/bundles/{bundle}/agents/{agent-name}.md`

### Script Verification (Conditional)

**Load when**: At least one deliverable creates, modifies, renames, or deletes a Python script.

When scripts are affected, load [standards/script-verification.md](standards/script-verification.md) which provides:
- Test creation/update requirements
- Test execution commands
- Test organization validation rules

Each script-related deliverable MUST include a **Script Verification** section per the standard.

---

## Integration

**Caller**: `pm-plugin-development:ext-outline-plugin-agent`

**Script Notations** (use EXACTLY as shown):
- `pm-workflow:manage-solution-outline:manage-solution-outline` - Write and validate solution document (write, validate, read, list-deliverables, exists) - validation is automatic on write
- `pm-workflow:manage-plan-documents:manage-plan-documents` - Request operations (request read, request create)
- `plan-marshall:lessons-learned:manage-lesson` - Record lessons on issues (add)
- `plan-marshall:logging:manage-log` - Log decisions and progress (work)
- `pm-workflow:manage-config:manage-config` - Plan config (read, get, set)
- `pm-workflow:manage-references:manage-references` - Plan references (read, get, set)
- `plan-marshall:marketplace-inventory:scan-marketplace-inventory` - Marketplace component inventory (see path-multi-workflow.md for usage):
  ```bash
  python3 .plan/execute-script.py plan-marshall:marketplace-inventory:scan-marketplace-inventory \
    --trace-plan-id {plan_id} \
    --include-descriptions
  ```

**Standards Referenced**:
- `pm-plugin-development:plugin-architecture` - Architecture principles
- `pm-plugin-development:plugin-script-architecture` - Script patterns and testing
- `pm-plugin-development:plugin-create` - Component creation patterns
- `pm-plugin-development:plugin-doctor` - Quality validation
