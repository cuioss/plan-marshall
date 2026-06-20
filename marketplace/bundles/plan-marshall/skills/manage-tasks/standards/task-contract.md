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
    {"number": 1, "target": "src/main/java/com/example/CacheConfig.java", "status": "pending", "intent": "write-new"},
    {"number": 2, "target": "src/main/java/com/example/CacheManager.java", "status": "pending", "intent": "write-replace"}
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
    {"number": 1, "target": "src/test/java/com/example/CacheTest.java", "status": "pending", "intent": "write-replace"}
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
    {"number": 1, "target": "./pw verify plan-marshall", "status": "pending", "intent": "read"}
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
| `status` | enum | Yes | Task status — `pending`/`in_progress`/`done`/`blocked`/`infeasible` (see Status Values) |
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
| `cost_size` | string | No | Predicted T-shirt cost size (`S`/`M`/`L`/`XL`), stamped by phase-4-plan from the cost-sizing rubric (see Cost-Sizing Fields below) |
| `predicted_cost_tokens` | integer | No | Predicted token cost for the task, stamped alongside `cost_size` (see Cost-Sizing Fields below) |
| `envelope_id` | integer | No | Bin-packer envelope-group identifier assigned by `manage-tasks pack-envelopes` (see Cost-Sizing Fields below) |

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
| `blocked` | Cannot proceed due to dependency or issue (recoverable — task may resume) |
| `infeasible` | Terminal explicit-triage outcome — the declared deliverable cannot be built as scoped (required surface absent, an assumed precondition is false, or building the named artifact is structurally impossible). Resolved by a gate-level planning decision (drop / re-scope into a new task / abort), never by resuming the same task |

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
   ├──────► blocked ◄──────┤
   │             │
   └──────► infeasible ◄───┘
```

`infeasible` has incoming edges from both `pending` (pre-work discovery — the
deliverable is recognised as unbuildable before any step runs) and `in_progress`
(mid-execute discovery — the deliverable turns out to be unbuildable during
execution), mirroring the `blocked` edges. Unlike `blocked`, `infeasible` is
terminal: there is no edge back to `pending`/`in_progress`.

| Current Status | Valid Transitions |
|---------------|-------------------|
| `pending` | `in_progress`, `blocked`, `infeasible` |
| `in_progress` | `done`, `blocked`, `infeasible` |
| `blocked` | `pending`, `in_progress` |
| `done` | (terminal) |
| `infeasible` | (terminal) |

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

### Mapping from Deliverable Dependencies

Deliverables use number-based `depends:` format. Task creation (phase-4-plan) converts as follows:

| Deliverable Format | Task Format |
|-------------------|-------------|
| `depends: none` | `"depends_on": []` |
| `depends: 1` | `"depends_on": ["TASK-1"]` |
| `depends: 1, 2` | `"depends_on": ["TASK-1", "TASK-2"]` |

The conversion parses the number prefix from each dependency reference.

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

## Cost-Sizing Fields

Three optional fields carry the plan-time cost prediction and envelope grouping used by the budget-bounded phase-5-execute task loop. They are stamped during phase-4-plan (`cost_size`, `predicted_cost_tokens`) and the bin-packing pass (`envelope_id`); they are absent on tasks created before sizing runs, and the `next` subcommand surfaces them as `null` in that case.

```toon
cost_size: M
predicted_cost_tokens: 60000
envelope_id: 2
```

| Field | Type | Producer | Description |
|-------|------|----------|-------------|
| `cost_size` | string | phase-4-plan (`derive-cost-size`) | T-shirt label `S`/`M`/`L`/`XL` |
| `predicted_cost_tokens` | integer | phase-4-plan (`derive-cost-size`) | Predicted token magnitude for the task |
| `envelope_id` | integer | bin-packer (`pack-envelopes`) | Group identifier binding the task to one budget envelope |

**Write path.** `derive-cost-size` and `pack-envelopes` are pure compute verbs — they emit the derived values but never mutate a task record. The single persistence path for all three fields is the `update` subcommand's cost-field flags: `--cost-size`, `--predicted-cost-tokens`, and `--envelope-id`. phase-4-plan stamps `cost_size`/`predicted_cost_tokens` via `update --cost-size … --predicted-cost-tokens …` (Step 6) and stamps `envelope_id` via `update --envelope-id …` (Step 7a). Validation at the write boundary: `--cost-size` must be one of `S`/`M`/`L`/`XL`, `--predicted-cost-tokens` must be non-negative, and `--envelope-id` must be a positive (1-based) integer. The persisted values round-trip back out through the `next` subcommand.

The size label vocabulary, the signal weights, the score thresholds, and the size→token table are owned by the central rubric — see [`../../phase-4-plan/standards/cost-sizing.md`](../../phase-4-plan/standards/cost-sizing.md). This contract does not restate the size-to-token mapping table; it only declares the schema fields that carry the rubric's output.

## Domain and Profile

### Domain Field

The `domain` field is inherited from the deliverable. Domains are arbitrary strings defined in `marshal.json`. Common examples:

| Domain | Description |
|--------|-------------|
| `java` | Production Java code |
| `javascript` | Production JavaScript code |
| `javascript-testing` | JavaScript test code (Jest, Cypress) |
| `plan-marshall-plugin-dev` | Marketplace plugin development |

### Profile Field

> Profiles follow the standard profile model. See [manage-contract.md](../../ref-workflow-architecture/standards/manage-contract.md) § Profiles for the canonical definition.

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
3. Copy verification from deliverable verbatim (already resolved during outline phase)
4. Generate steps from file lists
5. Compute task dependencies (testing depends on implementation)
6. Identify parallelizable tasks

**Constraint**: Each task maps to exactly one deliverable. No aggregation.

## Atomic Batch Insertion (`batch-add`)

The `batch-add` subcommand creates multiple tasks atomically — either every
task in the input array is persisted or no `TASK-NNN.json` file is created.
This is the canonical path for callers that already hold a list of structured
task records (e.g. `phase-4-plan` after composing tasks across deliverables).

### Semantics

- **All-or-nothing**: every entry is validated before any file is written. A
  single rejected entry aborts the entire batch with the original on-disk
  state untouched.
- **Sequential numbering**: numbers start at the next available slot at call
  time and increment in array order. Numbers are immutable on success and
  collisions are impossible because allocation happens once per call.
- **Empty array** (`"[]"`) is a documented no-op that returns
  `tasks_created: 0`.
- **Origin defaults**: when an entry omits `origin`, it defaults to `plan` —
  identical to the single-task add flow.
- **Logging**: a single `[MANAGE-TASKS] batch-add created {N} tasks` entry is
  written to `work.log`, summarising the assigned number range.

### JSON Array Schema

Each entry in the array is a JSON object with the same field semantics as the
TOON task definition consumed by `commit-add`. Field types:

```jsonc
[
  {
    "title": "Implement CacheConfig",                 // string, required
    "deliverable": 1,                                  // integer, required (0 only for holistic origin)
    "domain": "java",                                  // string, required
    "profile": "implementation",                       // string, default "implementation"
    "origin": "plan",                                  // string, default "plan"
    "description": "Create CacheConfig with Redis…",   // string, optional
    "skills": ["pm-dev-java:java-core"],               // string[], optional
    "depends_on": [],                                  // string[] OR comma-separated string OR "none"
    "steps": [                                         // {target, intent} object[], required (≥ 1)
      {"target": "src/main/java/CacheConfig.java", "intent": "write-new"}
    ],
    "verification": {                                  // object, optional
      "commands": ["mvn test -Dtest=CacheConfigTest"], // string[]
      "criteria": "All tests pass",                    // string
      "manual": false                                  // bool
    }
  }
]
```

### Field Rules

| Field | Required | Notes |
|-------|----------|-------|
| `title` | Yes | Non-empty string |
| `deliverable` | Yes | Non-negative integer; `0` only valid when `origin == "holistic"` |
| `domain` | Yes | Non-empty string (validated against marshal.json at execution) |
| `profile` | No (default `implementation`) | Step-path validation is skipped when `profile == "verification"` |
| `origin` | No (default `plan`) | Must match the standard origin set (`plan`, `fix`, `sonar`, `pr`, `lint`, `security`, `documentation`, `holistic`) |
| `skills` | No | Each entry must follow `bundle:skill` format |
| `depends_on` | No | Accepts a JSON array of `TASK-N`/integer strings, a comma-separated string, or `"none"` |
| `steps` | Yes | Array of `{target, intent}` objects (bare strings rejected); `intent` ∈ `read`/`write-new`/`write-replace`/`delete`; for non-verification profiles every `target` must look like a file path |
| `verification.commands` | No | Strings only (no list-of-list); copied verbatim |

### Failure Modes

| Cause | Response |
|-------|----------|
| Payload missing or empty | `error: error`, message `batch-add requires a JSON array via --tasks-json or stdin` |
| Payload not valid JSON | `error: error`, message includes line/column |
| Payload not a JSON array | `error: error`, message names the actual top-level type |
| Any entry fails validation | `error: error`, message prefixed with `batch entry [{index}]:` |
| Filesystem write error mid-batch | `error: error`, message starts with `batch-add aborted while writing tasks:`; any partially-written files are removed |

### Success Output

```toon
status: success
plan_id: EXAMPLE-PLAN
tasks_created: 3
starting_task_number: 4
total_tasks: 6
tasks[3]{number,title,file,domain,profile,deliverable,origin,step_count}:
  4,Implement CacheConfig,TASK-004.json,java,implementation,1,plan,1
  5,Test CacheConfig,TASK-005.json,java,module_testing,1,plan,1
  6,Wire CacheManager,TASK-006.json,java,implementation,2,plan,2
```

The `tasks` table reports each created task with its assigned number. Use this
in callers that need to log per-task creation events after a successful batch.

## Task Creation API

Uses a two-step `prepare-add` → `commit-add` flow to avoid shell metacharacter issues. `prepare-add` allocates a scratch path; the caller writes the YAML body to that path; `commit-add` reads the prepared file and creates `TASK-NNN.json`.

```bash
# Step 1: allocate a scratch path for the pending task definition
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks prepare-add \
  --plan-id {plan_id}
```

The command returns the scratch `path` (and `draft_id`/slot identifier). Write the task YAML to that path with the `Write` tool:

```yaml
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
  - {file_1} (write-new)
  - {file_2} (write-replace)
  - {file_3} (read)

depends_on: TASK-001

verification:
  commands:
    - {cmd1}
    - {cmd2}
  criteria: {criteria}
```

```bash
# Step 2: read the prepared file and create TASK-NNN.json
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks commit-add \
  --plan-id {plan_id}
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

Every step carries a **required** `intent` marker (see the Intent section below). Two input forms are accepted; bare-string steps are rejected on both.

**TOON (`commit-add`)** — each step is `target (intent)`, the intent in a trailing parenthesis:

```yaml
steps:
  - marketplace/bundles/plan-marshall/agents/execution-context.md (write-replace)
  - marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md (write-replace)
  - marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md (write-replace)
```

**JSON batch (`batch-add --tasks-file`)** — each step is a `{target, intent}` object:

```json
"steps": [
  {"target": "marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md", "intent": "write-replace"}
]
```

A bare TOON path with no `(intent)` suffix, or a bare-string JSON step, is rejected at parse time.

### Step Intent (required)

Each step declares a required `intent` from the closed enum `read` / `write-new` / `write-replace` / `delete`. There is no default — a step without a valid intent is a schema violation rejected at task-creation time. The intent drives the `files_exist` Q-Gate's per-target existence expectation:

| Intent | Meaning | files_exist expectation |
|--------|---------|-------------------------|
| `read` | Consulted, not modified | Existence required (finding if missing) |
| `write-new` | Created fresh | Existence forbidden (finding if it already exists) |
| `write-replace` | Modified in place | No existence check |
| `delete` | Removed | Existence required (finding if missing) |

#### Intent override (escape hatch)

Intent is **authoritative**, but may legitimately need to change after authoring — either from execution-time divergence (e.g. a `write-new` target turns out to already exist) OR from a finding (a PR review comment, Sonar issue, or build/lint finding resolved during verification/finalize that reveals the original classification was wrong). A step's stored intent may be altered ONLY via the sanctioned verb:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks update-step \
  --plan-id PLAN_ID --task-number N --step-number M \
  --intent INTENT --reason "why the intent changed" [--finding-id FINDING_ID]
```

`--reason` is **mandatory and persisted** as a `{from, to, reason}` audit record appended to the step's `intent_override` list; `--finding-id` is optional and links a triage-driven override back to its `manage-findings` finding. Hand-editing a stored `intent` value is a contract violation — and because `task_state_hash` folds in each step's `intent`, an undocumented out-of-band change additionally surfaces as phase-handshake drift. A step that was never overridden carries no `intent_override` key.

### Stored Format (.json files)

The script converts input to JSON array format in task files; each step carries `number`, `target`, `status`, and `intent`:

```json
{
  "steps": [
    {"number": 1, "target": "marketplace/bundles/plan-marshall/agents/execution-context.md", "status": "pending", "intent": "write-replace"},
    {"number": 2, "target": "marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md", "status": "pending", "intent": "write-replace"},
    {"number": 3, "target": "marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md", "status": "pending", "intent": "write-replace"}
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
  - Update execution-context to use TOON output
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
7. Every step's `intent` is required and must be one of `read` / `write-new` / `write-replace` / `delete`; bare-string steps (no intent) are rejected
8. Task `done` status requires all steps to be `done` or `skipped`
9. Task `done` status requires verification to have passed
