---
name: solution-outline
description: Domain-agnostic solution outline creation for thin agent workflow pattern
allowed-tools: Read, Glob, Grep, Bash
implements: pm-workflow:plan-wf-skill-api/solution-outline-skill-contract
---

# Solution Outline Skill

**Role**: Domain-agnostic workflow skill for creating solution outlines. Loaded by `pm-workflow:solution-outline-agent` to transform the request into a solution document by analyzing the codebase.

**Key Pattern**: Thin agent loads this skill and provides domain context. This skill performs codebase analysis and creates deliverables with explicit domain assignment.

## Contract Compliance

**MANDATORY**: All deliverables MUST follow the structure defined in the central contracts:

| Contract | Location | Purpose |
|----------|----------|---------|
| Deliverable Contract | `pm-workflow:manage-solution-outline/standards/deliverable-contract.md` | Required deliverable structure |
| Solution Outline Skill Contract | `pm-workflow:plan-wf-skill-api/standards/solution-outline-skill-contract.md` | Skill responsibilities |

**Key Requirements**:
- Every deliverable requires `domain` field (single value from `config.domains`)
- Every deliverable requires `profile` field (`implementation` or `testing`)
- `**Affected files:**` must list explicit file paths (no wildcards)
- `**Verification:**` must include automatable commands
- Validation is automatic on write - non-compliant deliverables are rejected

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `feedback` | string | No | User feedback for revision iterations |

## Workflow

### Step 0: Load Supporting Skills

Load the solution outline management skill for structure and examples:

```
Skill: pm-workflow:manage-solution-outline
```

This provides:
- Required document structure (Summary, Overview, Deliverables)
- ASCII diagram patterns
- Deliverable reference format
- Realistic examples

### Step 1: Load Request Context

Load plan context via manage-* scripts:

```bash
# Read original request description
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents \
  request read \
  --plan-id {plan_id}

# Read plan configuration (includes domains array)
python3 .plan/execute-script.py pm-workflow:manage-config:manage-config read \
  --plan-id {plan_id}

# Read references (issue context if available)
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references read \
  --plan-id {plan_id}
```

Extract `domains` array from config.toon - each deliverable will be assigned a single domain from this array.

### Step 1b: Load Project Architecture Context (Optional)

Load project architecture for intelligent placement decisions:

```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline \
  get-module-context
```

If architecture exists, output includes:
- **modules**: List with name, path, purpose, responsibility, key_packages, tips, insights, skill_domains

Use this context when determining:
- Which module should own new components
- Correct package paths within modules
- Applicable skill domains for implementation

If `status: not_found`, proceed without - use standard codebase analysis.

### Step 2: Analyze Codebase

Parse request intent and explore affected components. Detection patterns vary by domain:

**Project Structure Detection**:
```bash
# Java
Glob **/pom.xml
Glob **/build.gradle*

# JavaScript
Glob **/package.json
Glob **/tsconfig.json
```

**Component Exploration**:
```bash
# Search for classes, functions, modules
Grep "{component_name}" --type {language_type}
Glob src/**/*.{extension}
Read {file-path}
```

**Identify**:
- Components, modules, files affected
- Package/directory structure and placement
- Dependencies and integration points
- Test requirements
- Complexity assessment

### Step 3: Create Solution Document

Create a single solution document containing all deliverables. Each deliverable should be:
- **Independent**: Can be implemented without other deliverables completing first (when possible)
- **Testable**: Has clear completion criteria
- **Sized**: Reasonable scope (not too large, not too small)
- **Domain-assigned**: Has explicit `domain` field from config.domains

Build a deliverables markdown section with numbered deliverables and required metadata:

```markdown
### 1. {Deliverable Title}

**Metadata:**
- change_type: {create|modify|refactor|migrate|delete}
- execution_mode: {automated|manual|mixed}
- domain: {single domain from config.domains}
- profile: {implementation|testing}
- depends: {none | N. Title | N, M}

{Technical deliverable description}

**Affected files:**
- `{path/to/file1}`
- `{path/to/file2}`

**Change per file:** {What will be created or modified in each file}

**Verification:**
- Command: `{verification command}`
- Criteria: {success criteria}

**Success Criteria:**
- {criterion 1}
- {criterion 2}

### 2. {Next Deliverable Title}
...
```

**Domain Assignment Rules**:
- Each deliverable gets exactly ONE domain from `config.domains`
- For multi-domain plans (e.g., fullstack), assign based on deliverable content
- Production code and test code should be separate deliverables (different profiles)

### Step 4: Write Solution Document

Write the solution document using heredoc. **Note**: Validation runs automatically on write - do NOT add a `--validate` flag (it doesn't exist):

```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline \
  write \
  --plan-id {plan_id} <<'EOF'
# Solution Outline

## Summary
{one-line summary}

## Overview
{ASCII diagram showing component relationships}

## Deliverables

### 1. {Deliverable Title}
{content per Step 3 format}
EOF
```

**Why heredoc?** Solution outlines contain ASCII diagrams and rich content that don't fit CLI parameter passing. Validation runs automatically on every write.

### Step 5: Record Issues as Lessons

On unexpected codebase state or ambiguity:

```bash
python3 .plan/execute-script.py plan-marshall:lessons-learned:manage-lesson add \
  --component-type skill \
  --component-name solution-outline \
  --category observation \
  --title "{issue summary}" \
  --detail "{context and resolution approach}"
```

### Step 6: Return Results

**Output**:
```toon
status: success
plan_id: {plan_id}
deliverable_count: {number of deliverables in solution document}
lessons_recorded: {count}
message: {error message if status=error}
```

## Profile Assignment

When creating deliverables, assign profile based on content:

| Content Type | Profile |
|--------------|---------|
| Production code implementation | `implementation` |
| Test code creation | `testing` |
| Mixed (prod + tests together) | Split into separate deliverables |

## Change Types

| Type | Description | When to Use |
|------|-------------|-------------|
| `create` | New file/component | Adding new functionality |
| `modify` | Update existing | Enhancing or fixing existing code |
| `refactor` | Restructure without behavior change | Code reorganization |
| `migrate` | Format/API migration | Technology upgrades |
| `delete` | Remove file/component | Cleanup operations |

## Execution Modes

| Mode | Description | Task-Plan Behavior |
|------|-------------|-------------------|
| `automated` | Can run without human intervention | Can aggregate |
| `manual` | Requires human judgment/action | Must split |
| `mixed` | Contains both auto and manual parts | Must split into separate tasks |

## Complexity Assessment

| Factor | Low | Medium | High |
|--------|-----|--------|------|
| Files affected | 1-3 | 4-8 | 9+ |
| Cross-module | No | 1 module | 2+ modules |
| Breaking changes | None | Internal | Public API |
| Dependencies | 0-2 | 3-5 | 6+ |
| Test coverage needed | Unit only | Unit + Integration | Full suite |

## Error Handling

### Component Not Found

| Scope | Action |
|-------|--------|
| `create` | Continue (expected - component doesn't exist yet) |
| `modify` | Warn and ask for clarification |
| `refactor` | Error and request correct path |

### Ambiguous Component

If multiple components match the name:
- List all matches with paths
- Ask user to select correct one

### Missing Domain Information

If `config.domains` is empty:
- Error: "No domains configured. Run init phase first."

## Integration

**Invoked by**: `pm-workflow:solution-outline-agent` (thin agent)

**Script Notations** (use EXACTLY as shown):
- `pm-workflow:manage-solution-outline:manage-solution-outline` - Write and validate solution document
- `pm-workflow:manage-plan-documents:manage-plan-documents` - Request operations
- `pm-workflow:manage-config:manage-config` - Plan config (read domains)
- `pm-workflow:manage-references:manage-references` - Plan references
- `plan-marshall:lessons-learned:manage-lesson` - Record lessons on issues

**Consumed By**:
- `pm-workflow:task-plan` skill (reads deliverables for task creation)
