# Task File Format Specification

Complete reference for the TOON format used by task files.

## File Naming Convention

```
TASK-{NNN}-{slug}.toon
```

- `{NNN}`: Zero-padded 3-digit number (001, 002, etc.)
- `{slug}`: Kebab-case derived from title (max 40 characters)

## File Structure

```toon
number: {integer}
title: {string}
status: {task_status}
phase: {phase_name}
created: {iso_timestamp}
updated: {iso_timestamp}

deliverables[{count}]:
- {deliverable_number_1}
- {deliverable_number_2}

depends_on: {none | TASK-N, TASK-M}

description: |
  {multiline_text}

delegation:
  skill: {bundle}:{skill-name}
  workflow: {workflow-name}
  domain: {domain_name}
  context_skills:
  - {optional-skill-1}
  - {optional-skill-2}

steps[{count}]{number,title,status}:
{step_number},{step_title},{step_status}
...

verification:
  commands[{count}]:
  - {command_1}
  - {command_2}
  criteria: {success_criteria}
  manual: {true|false}

current_step: {integer}
```

## Field Definitions

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `number` | Yes | Integer | Unique task identifier (immutable after creation) |
| `title` | Yes | String | Short descriptive title |
| `status` | Yes | Enum | Task status (see Status Values) |
| `phase` | Yes | String | Plan phase: `1-init`, `2-outline`, `3-plan`, `4-execute`, `5-finalize` |
| `created` | Yes | ISO timestamp | When task was created |
| `updated` | Yes | ISO timestamp | When task was last modified |
| `deliverables` | Yes | Integer[] | List of deliverable numbers from solution_outline.md |
| `depends_on` | Yes | String | Task dependencies: `none` or TASK-N references |
| `description` | Yes | Multiline | Detailed task description |
| `delegation.skill` | Yes | String | Skill to load for execution (`{bundle}:{skill}`) |
| `delegation.workflow` | Yes | String | Workflow within the skill |
| `delegation.domain` | Yes | String | Skill domain for loading defaults |
| `delegation.context_skills` | No | String[] | Optional skills from domain's optionals |
| `steps` | Yes | Array | Ordered list of steps (at least one) |
| `verification.commands` | Yes | String[] | Commands to verify completion |
| `verification.criteria` | Yes | String | Success criteria description |
| `verification.manual` | No | Boolean | true if requires human verification |
| `current_step` | Yes | Integer | Current step number for execution |

## Status Values

### Task Status

| Value | Description |
|-------|-------------|
| `pending` | Task has not been started |
| `in_progress` | Task is currently being worked on |
| `done` | All steps completed, verification passed |
| `blocked` | Cannot proceed due to dependency or issue |

### Step Status

| Value | Description |
|-------|-------------|
| `pending` | Step has not been started |
| `in_progress` | Step is currently being executed |
| `done` | Step has been completed successfully |
| `skipped` | Step was intentionally skipped |

## State Transitions

### Task State Machine

```
pending ──► in_progress ──► done
   │             │
   │             ▼
   └──────► blocked
```

| Current Status | Valid Transitions |
|---------------|-------------------|
| `pending` | `in_progress`, `blocked` |
| `in_progress` | `done`, `blocked` |
| `blocked` | `pending`, `in_progress` |
| `done` | (terminal) |

### Step State Machine

```
pending ──► in_progress ──► done
   │
   └──────► skipped
```

## Phase Values

| Phase | Description |
|-------|-------------|
| `init` | Setup tasks (create directories, configs) |
| `outline` | Solution outline creation |
| `plan` | Task planning and skill resolution |
| `execute` | Implementation tasks (code changes) |
| `finalize` | Cleanup tasks (docs, release) |

## Domain Values

Domains are arbitrary strings defined in `marshal.json`. Common examples:

| Domain | Description |
|--------|-------------|
| `java` | Production Java code |
| `javascript` | Production JavaScript code |
| `javascript-testing` | JavaScript test code (Jest, Cypress) |
| `plan-marshall-plugin-dev` | Claude Code marketplace plugin development |

## Dependency Format

### File Format (stored in .toon files)

| Value | Meaning |
|-------|---------|
| `depends_on: none` | No dependencies, can start immediately |
| `depends_on: TASK-1` | Depends on TASK-1 completing |
| `depends_on: TASK-1, TASK-2` | Depends on both TASK-1 and TASK-2 completing |

### Rules

- Task cannot start until all dependencies are `done`
- Circular dependencies are invalid
- Dependencies enable parallel execution planning
- Task references use format `TASK-N` (e.g., `TASK-1`, `TASK-2`)

## Verification Block

The verification block defines how to verify task completion:

```toon
verification:
  commands[2]:
  - ./gradlew test --tests *AuthController*
  - curl -s http://localhost:8080/auth | jq .status
  criteria: All tests pass and endpoint responds
  manual: false
```

| Field | Required | Description |
|-------|----------|-------------|
| `commands` | Yes | List of shell commands to run |
| `criteria` | Yes | Human-readable success description |
| `manual` | No | Set to `true` if requires human verification |

## Numbering Rules

### Task Numbers

- Assigned incrementally (next available number)
- Numbers are **immutable** - removal creates gaps
- References use `TASK-{n}` format (stable references)

### Step Numbers

- Numbered 1 to N within each task
- Renumbered when steps are added or removed
- Always sequential (no gaps)

## Example

```toon
number: 2
title: Add Auth Endpoint
status: in_progress
phase: execute
created: 2025-12-02T10:30:00Z
updated: 2025-12-02T11:00:00Z

deliverables[2]:
- 1
- 4

depends_on: TASK-1

description: |
  Create REST endpoint for user authentication.
  Endpoint should accept username/password and
  return JWT token on successful auth.

delegation:
  skill: pm-dev-java:java-implement
  workflow: implement
  domain: java
  context_skills:
  - pm-dev-java:java-cdi

steps[3]{number,title,status}:
1,Create AuthController class,done
2,Add request/response DTOs,in_progress
3,Write integration tests,pending

verification:
  commands[2]:
  - ./gradlew test --tests *AuthController*
  - curl -s http://localhost:8080/auth | jq .status
  criteria: All tests pass and endpoint responds
  manual: false

current_step: 2
```

## Validation Rules

1. At least one step is required
2. `current_step` must be within valid step range (1 to step_count)
3. `deliverables` must be non-empty list of positive integers
4. `delegation.skill` must follow `{bundle}:{skill}` format
5. `delegation.domain` must be a valid domain value
6. Task `done` status requires all steps to be `done` or `skipped`
7. Task `done` status requires verification to have passed
