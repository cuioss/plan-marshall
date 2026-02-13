# Task File Format Specification

Complete reference for the JSON format used by task files.

## File Naming Convention

```
TASK-{NNN}.json
```

- `{NNN}`: Zero-padded 3-digit number (001, 002, etc.)
- Task type is stored in the JSON `type` field, not in the filename

## File Structure

```json
{
  "number": 1,
  "title": "Create Auth Endpoint",
  "status": "pending",
  "phase": "5-execute",
  "domain": "java",
  "profile": "implementation",

  "origin": "plan",
  "deliverable": 1,
  "depends_on": ["TASK-1"],
  "skills": ["pm-dev-java:java-core", "pm-dev-java:java-cdi"],
  "description": "Create REST endpoint for user authentication...",
  "steps": [
    {"number": 1, "target": "src/main/java/AuthController.java", "status": "done"},
    {"number": 2, "target": "src/main/java/AuthDTO.java", "status": "in_progress"},
    {"number": 3, "target": "src/test/java/AuthControllerTest.java", "status": "pending"}
  ],
  "verification": {
    "commands": ["./gradlew test --tests *AuthController*"],
    "criteria": "All tests pass",
    "manual": false
  },
  "current_step": 2
}
```

## Field Definitions

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `number` | Yes | Integer | Unique task identifier (immutable after creation) |
| `title` | Yes | String | Short descriptive title |
| `status` | Yes | Enum | Task status (see Status Values) |
| `phase` | Yes | String | Plan phase: `1-init`, `2-refine`, `3-outline`, `4-plan`, `5-execute`, `6-verify`, `7-finalize` |
| `deliverable` | Yes | Integer | Deliverable number from solution_outline.md (1:1 constraint) |
| `depends_on` | Yes | String[] | Task dependencies: empty array or TASK-N references |
| `description` | Yes | String | Detailed task description |
| `domain` | Yes | String | Task domain (java, javascript, plugin, etc.) |
| `profile` | Yes | String | Task profile for executor routing (implementation, module_testing) |
| `origin` | Yes | String | Task origin: `plan`, `fix`, `sonar`, `pr`, `lint`, `security`, `documentation` |
| `skills` | Yes | String[] | Skills to load for execution (`{bundle}:{skill}`) |
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
| `1-init` | Setup tasks (create directories, configs) |
| `3-outline` | Solution outline creation |
| `4-plan` | Task planning and skill resolution |
| `5-execute` | Implementation tasks (code changes) |
| `7-finalize` | Cleanup tasks (docs, release) |

## Domain Values

Domains are arbitrary strings defined in `marshal.json`. Common examples:

| Domain | Description |
|--------|-------------|
| `java` | Production Java code |
| `javascript` | Production JavaScript code |
| `javascript-testing` | JavaScript test code (Jest, Cypress) |
| `plan-marshall-plugin-dev` | Claude Code marketplace plugin development |

## Dependency Format

### File Format (stored in .json files)

| Value | Meaning |
|-------|---------|
| `"depends_on": []` | No dependencies, can start immediately |
| `"depends_on": ["TASK-1"]` | Depends on TASK-1 completing |
| `"depends_on": ["TASK-1", "TASK-2"]` | Depends on both TASK-1 and TASK-2 completing |

### Rules

- Task cannot start until all dependencies are `done`
- Circular dependencies are invalid
- Dependencies enable parallel execution planning
- Task references use format `TASK-N` (e.g., `TASK-1`, `TASK-2`)

## Verification Block

The verification block defines how to verify task completion:

```json
{
  "verification": {
    "commands": [
      "./gradlew test --tests *AuthController*",
      "curl -s http://localhost:8080/auth | jq .status"
    ],
    "criteria": "All tests pass and endpoint responds",
    "manual": false
  }
}
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

```json
{
  "number": 2,
  "title": "Add Auth Endpoint",
  "status": "in_progress",
  "phase": "5-execute",
  "domain": "java",
  "profile": "implementation",

  "origin": "plan",
  "deliverable": 1,
  "depends_on": ["TASK-1"],
  "skills": ["pm-dev-java:java-core", "pm-dev-java:java-cdi"],
  "description": "Create REST endpoint for user authentication.\nEndpoint should accept username/password and\nreturn JWT token on successful auth.",
  "steps": [
    {"number": 1, "target": "src/main/java/AuthController.java", "status": "done"},
    {"number": 2, "target": "src/main/java/AuthDTO.java", "status": "in_progress"},
    {"number": 3, "target": "src/test/java/AuthControllerTest.java", "status": "pending"}
  ],
  "verification": {
    "commands": [
      "./gradlew test --tests *AuthController*",
      "curl -s http://localhost:8080/auth | jq .status"
    ],
    "criteria": "All tests pass and endpoint responds",
    "manual": false
  },
  "current_step": 2
}
```

## Validation Rules

1. At least one step is required
2. `current_step` must be within valid step range (1 to step_count)
3. `deliverable` must be a positive integer
4. `skills` entries must follow `{bundle}:{skill}` format
5. `domain` must be a valid domain value
6. `profile` must be a valid profile value (implementation, module_testing)
7. Task `done` status requires all steps to be `done` or `skipped`
8. Task `done` status requires verification to have passed
