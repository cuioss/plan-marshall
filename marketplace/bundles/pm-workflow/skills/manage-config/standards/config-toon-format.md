# Config TOON Format

Defines the structure of `config.toon` after init phase. This file stores plan-level configuration settings.

## Purpose

The `config.toon` file:
- Stores detected domains (array) for the plan
- Provides commit and branch strategy settings
- Contains finalization settings
- Tracks current plan phase

Note: `workflow_skills` are NOT stored in config.toon. They are resolved at runtime from `marshal.json` via `plan-marshall-config resolve-workflow-skill`.

## File Format

```toon
# Plan identification
plan_id: my-feature-123
phase: execute

# Multiple domains supported (e.g., fullstack feature)
domains:
  - java
  - javascript

commit_strategy: per_task

# Finalize settings
create_pr: true
verification_required: true
verification_command: /pm-dev-builder:builder-build-and-fix
branch_strategy: feature
```

## Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `plan_id` | string | Unique plan identifier |
| `phase` | string | Current phase: 1-init, 2-outline, 3-plan, 4-execute, 5-finalize |
| `domains` | list | Array of detected domains (set during outline phase) |
| `commit_strategy` | string | per_task, per_plan, or none |
| `create_pr` | boolean | Whether to create PR on finalize |
| `verification_required` | boolean | Whether to run verification before PR |
| `verification_command` | string | Command to run for verification |
| `branch_strategy` | string | feature or direct |

## Phase Values

| Phase | Description | Sets |
|-------|-------------|------|
| `1-init` | Plan initialization | `plan_id`, `phase=1-init` |
| `2-outline` | Solution outline creation | `domains`, `phase=2-outline` |
| `3-plan` | Task planning | `phase=3-plan` |
| `4-execute` | Task execution | `phase=4-execute` |
| `5-finalize` | Verification and commit | `phase=5-finalize` |

## Domains Array

The `domains` array is set during the outline phase and supports multi-domain plans:

| Scenario | Example | Domains |
|----------|---------|---------|
| Java backend feature | Add caching to UserService | `[java]` |
| Frontend feature | Add dashboard component | `[javascript]` |
| Fullstack feature | Add metrics API + dashboard | `[java, javascript]` |
| Plugin development | Create new skill | `[plan-marshall-plugin-dev]` |

Each deliverable/task selects ONE domain from this array.

## Workflow Skills Resolution

Workflow skills are resolved at runtime from `marshal.json`:

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  resolve-workflow-skill --phase {phase}
```

| Phase | Purpose |
|-------|---------|
| `init` | Skill for plan initialization |
| `outline` | Skill for creating solution outlines |
| `plan` | Skill for task planning |
| `execute` | Skill for task execution (profile-based) |
| `finalize` | Skill for verification and commit |

### Phase Workflow Resolution

```bash
# Resolve workflow skill for each phase
resolve-workflow-skill --phase 1-init       # → pm-workflow:phase-1-init
resolve-workflow-skill --phase 2-outline    # → pm-workflow:phase-2-outline
resolve-workflow-skill --phase 3-plan       # → pm-workflow:phase-3-plan
resolve-workflow-skill --phase 5-finalize   # → pm-workflow:phase-5-finalize

# Execute phase uses domain and profile from task
resolve-workflow-skill --domain java --phase implementation  # → system fallback or domain override
```

## Workflow Phase Usage

| Phase | Operation | Purpose |
|-------|-----------|---------|
| 1-Init | Creates config.toon | Stores plan_id, initializes phase |
| 2-Outline | Sets domains | Analyzes request, sets domains |
| 3-Plan | Reads domains | Creates tasks with domain/profile |
| 4-Execute | Reads domains | Executes tasks using task.skills |
| 5-Finalize | Reads settings | Runs verification, creates PR |

## Commit Strategy

| Strategy | Behavior |
|----------|----------|
| `per_task` | One commit per completed task |
| `per_plan` | Single commit for all tasks |
| `none` | No commits (manual) |

## Branch Strategy

| Strategy | Behavior |
|----------|----------|
| `feature` | Create feature branch from main |
| `direct` | Work on current branch |

## Finalize Settings

| Field | Description |
|-------|-------------|
| `create_pr` | Create pull request when all tasks complete |
| `verification_required` | Run verification before PR creation |
| `verification_command` | Command to execute for verification |

## Key Architectural Points

1. **Plan level**: `domains` is an array (supports multi-domain plans)
2. **Deliverable level**: Each deliverable has single `domain` field
3. **Task level**: Each task has single `domain` and `profile` field
4. **Runtime resolution**: workflow_skills resolved from marshal.json (not stored in config.toon)
5. **Same resolve path**: All domains use same resolution via `resolve-workflow-skill` command
6. **Domains set during outline**: Outline phase determines relevant domains from analysis

## Example: Single Domain (Java)

```toon
plan_id: add-caching-feature
phase: execute

domains:
  - java

commit_strategy: per_task
create_pr: true
verification_required: true
verification_command: /pm-dev-builder:builder-build-and-fix
branch_strategy: feature
```

## Example: Multi-Domain (Fullstack)

```toon
plan_id: metrics-dashboard
phase: plan

domains:
  - java
  - javascript

commit_strategy: per_task
create_pr: true
verification_required: true
verification_command: /pm-dev-builder:builder-build-and-fix
branch_strategy: feature
```

## Example: Plugin Domain

```toon
plan_id: new-skill-creation
phase: outline

domains:
  - plan-marshall-plugin-dev

commit_strategy: per_task
create_pr: true
verification_required: true
verification_command: python3 test/run-tests.py
branch_strategy: feature
```

---

## Related Documents

- `pm-workflow:phase-1-init/SKILL.md` - Init phase creates config.toon
- `pm-workflow:phase-2-outline/SKILL.md` - Outline phase sets domains
- `pm-workflow:workflow-extension-api/standards/architecture.md` - Workflow architecture overview
