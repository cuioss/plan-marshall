# Plan Init Skill Contract

Initialize plan structure with status.toon, config.toon, and references.toon.

**Implementation**: `pm-workflow:phase-init`

---

## Purpose

The init phase creates the plan directory structure and initial files needed for subsequent phases. It is the entry point for all plan workflows.

---

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier (kebab-case) |
| `title` | string | Conditional | Plan title for display (if not from lesson) |
| `issue_url` | string | No | GitHub issue URL if plan is from issue |
| `lesson_id` | string | No | Lesson ID to convert to plan |
| `branch` | string | No | Git branch name (auto-generated if not provided) |

**Source mutual exclusivity**: Provide ONE of: `title`, `issue_url`, or `lesson_id`.

---

## Output

### Directory Structure Created

```
.plan/plans/{plan_id}/
├── status.toon        # Plan lifecycle state
├── config.toon        # Plan configuration
└── references.toon    # File and branch references
```

### Files Created

#### status.toon

```toon
title: {title}
current_phase: init
phases[5]{name,status}:
init,in_progress
outline,pending
plan,pending
execute,pending
finalize,pending

created: {timestamp}
updated: {timestamp}
```

#### config.toon

```toon
plan_id: {plan_id}
domains: []              # Empty until outline phase detects domains
```

#### references.toon

```toon
branch: {branch}
base_branch: main
issue_url: {issue_url}   # If provided
modified_files: []
config_files: []
test_files: []
```

---

## Workflow

### Step 1: Validate Input

Validate:
- `plan_id` format (kebab-case)
- Plan doesn't already exist

### Step 2: Create Plan Directory

```bash
python3 .plan/execute-script.py pm-workflow:manage-lifecycle:manage-lifecycle create \
  --plan-id {plan_id} \
  --title "{title}" \
  --phases init,outline,plan,execute,finalize
```

### Step 3: Create Config

```bash
python3 .plan/execute-script.py pm-workflow:manage-config:manage-config create \
  --plan-id {plan_id}
```

### Step 4: Create References

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references create \
  --plan-id {plan_id} \
  --branch {branch} \
  [--issue-url {issue_url}]
```

### Step 5: Create Git Branch

If branch doesn't exist, create it:

```bash
git checkout -b {branch}
```

### Step 6: Transition to Outline

```bash
python3 .plan/execute-script.py pm-workflow:manage-lifecycle:manage-lifecycle transition \
  --plan-id {plan_id} \
  --completed init
```

---

## Auto-Continue

Init phase **auto-continues** to outline phase. No user approval gate.

```
init ──auto──▶ outline
```

---

## Skill Loading

Init phase uses **system defaults only**:

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  skill-domains get-defaults --domain system
```

No domain-specific skills are loaded during init (domains not yet determined).

---

## Error Handling

### plan_exists

When the plan already exists, prompt the user with options:

```
AskUserQuestion:
  question: "Plan '{plan_id}' already exists. What would you like to do?"
  header: "Plan exists"
  options:
    - label: "Resume"
      description: "Continue with the existing plan"
    - label: "Replace"
      description: "Delete existing plan and create new"
    - label: "Rename"
      description: "Choose a different plan ID"
```

**Option handling**:
- **Resume**: Skip to output with existing plan data
- **Replace**: Delete existing plan via `manage-files delete-plan`, then re-run create
- **Rename**: Prompt for new plan_id, re-run from Step 1

### Other Errors

| Error | Cause | Recovery |
|-------|-------|----------|
| `invalid_plan_id` | Plan ID not kebab-case | Return error, user must provide valid format |
| `branch_exists` | Git branch already exists | Use existing branch or prompt for different name |

---

## Output Format

### Success

```toon
status: success
plan_id: {plan_id}
phase: init
files_created:
  - status.toon
  - config.toon
  - references.toon
branch: {branch}
next_phase: outline
auto_continue: true
```

### Error

```toon
status: error
plan_id: {plan_id}
error: plan_exists
message: "Plan '{plan_id}' already exists"
```

---

## Related Documents

- [solution-outline-skill-contract.md](solution-outline-skill-contract.md) - Next phase (outline)
- [architecture-overview.md](architecture-overview.md) - Phase flow overview
- [config-toon-format.md](config-toon-format.md) - Config.toon structure
