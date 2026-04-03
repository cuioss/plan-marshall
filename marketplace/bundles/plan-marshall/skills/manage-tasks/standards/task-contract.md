# Task Contract

Standard structure for tasks created by task-plan skills. Tasks represent committable units of work derived from deliverables with pre-resolved skills for 6-phase workflow execution.

## Purpose

Each task:

- References exactly one deliverable (1:1 constraint)
- Contains domain and profile for workflow routing
- Includes explicit skills array (pre-resolved during task creation)
- Includes verification criteria
- Specifies dependencies on other tasks (for ordering/parallelization)
- Results in exactly one commit
- Tracks origin (plan or fix) for finalize loop handling

## Task File Format (JSON)

Tasks are stored as JSON files: `TASK-{NNN}.json`

### Regular Task (from plan phase)

```json
{
  "number": 1,
  "title": "Create CacheConfig class",
  "status": "pending",
  "domain": "java",
  "profile": "implementation",
  "origin": "plan",
  "skills": ["pm-dev-java:java-core", "pm-dev-java:java-cdi"],
  "deliverable": 1,
  "depends_on": [],
  "description": "Create CacheConfig class with Redis configuration...",
  "steps": [
    {"number": 1, "target": "src/main/java/com/example/CacheConfig.java", "status": "pending"},
    {"number": 2, "target": "src/main/java/com/example/CacheManager.java", "status": "pending"}
  ],
  "verification": {
    "commands": ["mvn test -Dtest=CacheConfigTest"],
    "criteria": "All tests pass",
    "manual": false
  },
  "current_step": 1
}
```

### Fix Task (from finalize phase)

```json
{
  "number": 3,
  "title": "Fix: Test failure in CacheTest",
  "status": "pending",
  "domain": "java",
  "profile": "module_testing",
  "origin": "fix",
  "skills": ["pm-dev-java:junit-core", "pm-dev-java:java-core"],
  "deliverable": 1,
  "depends_on": ["TASK-2"],
  "description": "Fix test failure detected during verification.",
  "finding": {
    "type": "test_failure",
    "file": "src/test/java/com/example/CacheTest.java",
    "line": 58,
    "message": "AssertionError: expected 5 but was 3"
  },
  "steps": [
    {"number": 1, "target": "src/test/java/com/example/CacheTest.java", "status": "pending"}
  ],
  "verification": {
    "commands": ["mvn test -Dtest=CacheTest"],
    "criteria": "Test passes",
    "manual": false
  },
  "current_step": 1
}
```

### Verification Task (no files to modify)

For `verification` profile tasks, steps contain verification commands instead of file paths. File-path validation is skipped for this profile.

```json
{
  "number": 6,
  "title": "Verify plan-marshall bundle",
  "status": "pending",
  "domain": "plan-marshall-plugin-dev",
  "profile": "verification",
  "origin": "plan",
  "skills": [],
  "deliverable": 6,
  "depends_on": ["TASK-5"],
  "description": "Run full verification suite for the plan-marshall bundle.",
  "steps": [
    {"number": 1, "target": "./pw verify plan-marshall", "status": "pending"}
  ],
  "verification": {
    "commands": ["./pw verify plan-marshall"],
    "criteria": "All tests, types, and linting pass",
    "manual": false
  },
  "current_step": 1
}
```

## Key Fields

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `number` | integer | Yes | Unique task identifier — immutable after creation |
| `title` | string | Yes | Task title for display |
| `status` | enum | Yes | Task status (see Status Values) |
| `domain` | string | Yes | Single domain from deliverable (java, javascript, plan-marshall-plugin-dev) |
| `profile` | string | Yes | Workflow profile (implementation, module_testing, integration_testing) |
| `skills` | list | Yes | Domain skills pre-resolved during task creation (`{bundle}:{skill}`) |
| `deliverable` | int | Yes | Referenced deliverable number (1:1 constraint) |
| `depends_on` | string[] | Yes | Task dependencies for ordering: empty array or `TASK-N` references |
| `origin` | string | Yes | Task origin (see Origin Field) |
| `description` | string | Yes | Detailed task description |
| `steps` | array | Yes | Ordered list of steps (at least one) |
| `verification` | object | Yes | Commands and criteria |
| `current_step` | integer | Yes | Current step number for execution |
| `priority` | string | No | Execution priority (fix tasks) |
| `finding` | object | No | Original finding details (fix tasks only) |

## Task ID Format

Tasks use sequential numbering with zero-padded format:

| Format | Example | Description |
|--------|---------|-------------|
| `TASK-{NNN}` | `TASK-001` | 3-digit zero-padded sequence |

**Filename format**: `TASK-{NNN}.json` (e.g., `TASK-001.json`, `TASK-003.json`)

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

## Numbering Rules

### Task Numbers

- Assigned incrementally (next available number)
- Numbers are **immutable** — removal creates gaps
- References use `TASK-{n}` format (stable references)

### Step Numbers

- Numbered 1 to N within each task
- Renumbered when steps are added or removed
- Always sequential (no gaps)

## Dependency Format

Dependencies are stored in the `depends_on` field as an array of task references:

| Value | Meaning |
|-------|---------|
| `"depends_on": []` | No dependencies, can start immediately |
| `"depends_on": ["TASK-1"]` | Depends on TASK-1 completing |
| `"depends_on": ["TASK-1", "TASK-2"]` | Depends on both TASK-1 and TASK-2 completing |

### Dependency Rules

- Task cannot start until all dependencies are `done`
- Circular dependencies are invalid
- Dependencies enable parallel execution planning
- Task references use format `TASK-N` (e.g., `TASK-1`, `TASK-2`)

## Origin Field

Indicates what created the task:

| Value | Source | Description |
|-------|--------|-------------|
| `plan` | plan phase | Task from deliverable (any change_type) |
| `fix` | verify/finalize | Generic fix from finding |
| `sonar` | Sonar analysis | Sonar issue fix |
| `pr` | PR review | PR review comment fix |
| `lint` | linting | Lint/format fix |
| `security` | security scan | Security finding fix |
| `documentation` | doc review | Documentation fix |

## Priority Field (Fix Tasks)

Task execution priority for fix tasks:

| Source | Default Priority |
|--------|------------------|
| plan phase | normal |
| finalize:sonar | By severity (BLOCKER→critical) |
| finalize:pr | high |
| finalize:security | critical |
| finalize:lint | low |

## Finding Field (Fix Tasks Only)

Original finding details for fix tasks:

```toon
finding:
  type: compilation_error
  file: src/main/java/com/example/CacheConfig.java
  line: 42
  message: "cannot find symbol: class RedisTemplate"
```

## Domain and Profile

### Domain Field

The `domain` field is inherited from the deliverable. Domains are arbitrary strings defined in `marshal.json`. Common examples:

| Domain | Description |
|--------|-------------|
| `java` | Production Java code |
| `javascript` | Production JavaScript code |
| `javascript-testing` | JavaScript test code (Jest, Cypress) |
| `plan-marshall-plugin-dev` | Claude Code marketplace plugin development |

### Profile Field

The `profile` field determines the workflow type:

| Profile | Description |
|---------|-------------|
| `implementation` | Create/modify production code |
| `module_testing` | Create/modify test code |
| `quality` | Documentation, verification |
| `verification` | Verification-only (no files to modify, runs commands only) |

## Skills Inheritance

Skills are resolved by task-plan from architecture based on deliverable's module and profile:

```
solution-outline phase               task-plan phase                     execute phase
┌────────────────────────┐           ┌─────────────────────────────┐     ┌────────────────────────┐
│ Deliverable:           │           │ For each profile:           │     │ Read task.skills       │
│   module: auth-service │──────────▶│   1. Query architecture     │────▶│ Load directly          │
│   profiles:            │           │      module --name {module} │     │ (no resolution call)   │
│     - implementation   │           │   2. Extract skills_by_     │     │                        │
│     - testing          │           │      profile.{profile}      │     │                        │
└────────────────────────┘           │   3. Create task with       │     └────────────────────────┘
                                     │      resolved skills        │
                                     └─────────────┬───────────────┘
                                                   │
                                     ┌─────────────▼───────────────┐
                                     │ TASK-001.json               │
                                     │ profile: implementation     │
                                     │ skills:                     │
                                     │   - pm-dev-java:java-core   │
                                     │   - pm-dev-java:java-cdi    │
                                     ├─────────────────────────────┤
                                     │ TASK-002.json               │
                                     │ profile: module_testing     │
                                     │ skills:                     │
                                     │   - pm-dev-java:java-core   │
                                     │   - pm-dev-java:junit-core  │
                                     │ depends_on: ["TASK-1"]      │
                                     └─────────────────────────────┘
```

## Skills Array

The `skills` array contains domain-specific skills resolved from architecture:

| Source | Description |
|--------|-------------|
| `architecture.module.skills_by_profile.{profile}` | Resolved by task-plan from architecture |

Task-plan resolves skills from architecture for each profile in the deliverable's profiles list.

**Two-tier skill loading at execution**:
- **Tier 1 (implicit)**: System skills loaded by agent automatically
- **Tier 2 (explicit)**: `task.skills` loaded by agent from task file

## Deliverable-to-Task Relationship

Tasks have a **1:1 constraint** with deliverables - each task references exactly one deliverable:

| Pattern | Description | Example |
|---------|-------------|---------|
| 1:1 | One task per deliverable | Single-profile deliverable |
| 1:N | One deliverable, multiple profiles | TASK-1 and TASK-2 both have `deliverable: 1` |

### 1:N Pattern

When a deliverable has multiple profiles (implementation + module_testing), it creates multiple tasks - one per profile. Both tasks reference the same deliverable number:

- TASK-1: `deliverable: 1`, `profile: implementation`
- TASK-2: `deliverable: 1`, `profile: module_testing`, `depends_on: ["TASK-1"]`

## Optimization Workflow

Task-plan skills MUST follow this workflow:

### Step 1: Load All Deliverables

Extract for each deliverable:
- `metadata.change_type`
- `metadata.execution_mode`
- `metadata.domain`
- `metadata.depends`
- `profiles` (list of profiles)
- `affected_files`
- `verification`

### Step 2: Build Dependency Graph

- Parse `depends` field for each deliverable
- Identify independent deliverables (`depends: none`)
- Identify dependency chains
- Detect cycles (INVALID - reject)

### Step 3: Analyze for Aggregation

For each pair of deliverables, check:
- Same change_type?
- Same domain and profile?
- Same execution_mode?
- Combined file count < 10?
- Verification can be merged?
- **NO dependency between them?** (CRITICAL)

Cannot aggregate if one depends on the other.

### Step 4: Analyze for Splits

For each deliverable, check:
- `execution_mode: mixed` -> MUST split
- Different concerns -> SHOULD split
- File count > 15 -> CONSIDER splitting

### Step 5: Create Tasks (1:N Mapping)

For each deliverable, for each profile in deliverable.profiles:
1. Resolve skills from architecture: `module.skills_by_profile.{profile}`
2. Set `domain` from deliverable, `profile` from current iteration
3. Copy verification from deliverable (Command + Criteria — verbatim, no resolution)
4. Generate steps from file lists
5. Compute task dependencies (testing depends on implementation)
6. Identify parallelizable tasks

**Constraint**: Each task maps to exactly one deliverable. No aggregation.

## Task Creation API

Uses stdin-based API with heredoc to avoid shell metacharacter issues:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks add \
  --plan-id {plan_id} <<'EOF'
title: {task title}
deliverable: {deliverable_number}
domain: {domain}
profile: {profile}
skills:
  - pm-dev-java:java-core
  - pm-dev-java:java-cdi
description: |
  {description from deliverable}

steps:
  - {file_1}
  - {file_2}
  - {file_3}

depends_on: TASK-001

verification:
  commands:
    - {cmd1}
    - {cmd2}
  criteria: {criteria}
EOF
```

## Task-Plan Output

```toon
status: success
plan_id: {plan_id}

summary:
  deliverables_processed: {N}
  tasks_created: {M}
  parallelizable_groups: {count of independent task groups}

tasks_created[M]{number,title,deliverable,depends_on}:
1,Implement UserService,1,none
2,Test UserService,1,TASK-1
3,Implement UserRepository,2,none
4,Test UserRepository,2,TASK-3

execution_order:
  parallel_group_1: [TASK-001, TASK-003]
  parallel_group_2: [TASK-002]
  parallel_group_3: [TASK-004]
  parallel_group_4: [TASK-005]

lessons_recorded: {count}
```

## Steps Field Contract

**CRITICAL**: The `steps` field MUST contain file paths from the deliverable's `Affected files` section. Exception: `verification` profile tasks use verification commands as steps instead of file paths (file-path validation is skipped).

### Input Format (API calls)

When calling `manage-tasks add`, use YAML list format:

```yaml
steps:
  - marketplace/bundles/plan-marshall/agents/phase-agent.md
  - marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md
  - marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md
```

### Stored Format (.json files)

The script converts input to JSON array format in task files:

```json
{
  "steps": [
    {"number": 1, "target": "marketplace/bundles/plan-marshall/agents/phase-agent.md", "status": "pending"},
    {"number": 2, "target": "marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md", "status": "pending"},
    {"number": 3, "target": "marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md", "status": "pending"}
  ]
}
```

### Valid Steps Requirements

**Why valid:**
- Each step is an explicit file path
- Steps are derived from deliverable's `Affected files`
- Execution progress can be tracked per file

### Invalid Steps (Descriptive Text)

```yaml
steps:
  - Update phase-agent to use TOON output
  - Migrate phase-3-outline skill output format
  - Convert all remaining components
```

**Why invalid:**
- Steps are action descriptions, not file paths
- Cannot track which files have been processed
- "all remaining agents" is vague
- Validation will reject this task

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

**Provenance**: The `commands` array is copied verbatim from the deliverable's `Verification: Command` field by phase-4-plan. Verification commands are resolved during the outline phase (phase-3-outline) — downstream phases do not re-resolve them.

## Validation Rules

1. At least one step is required
2. `current_step` must be within valid step range (1 to step_count)
3. `deliverable` must be a positive integer
4. `skills` entries must follow `{bundle}:{skill}` format
5. `domain` must be a valid domain value
6. `profile` must be a valid profile value (implementation, module_testing, verification)
7. Task `done` status requires all steps to be `done` or `skipped`
8. Task `done` status requires verification to have passed
