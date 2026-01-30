# Task Contract

Standard structure for tasks created by task-plan skills. Tasks represent committable units of work derived from deliverables with pre-resolved skills for 7-phase workflow execution.

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

Tasks are stored as JSON files: `TASK-{NNN}-{TYPE}.json`

### Regular Task (from plan phase)

```json
{
  "number": 1,
  "title": "Create CacheConfig class",
  "status": "pending",
  "phase": "5-execute",
  "domain": "java",
  "profile": "implementation",
  "type": "IMPL",
  "origin": "plan",
  "skills": ["pm-dev-java:java-core", "pm-dev-java:java-cdi"],
  "deliverable": 1,
  "depends_on": [],
  "description": "Create CacheConfig class with Redis configuration...",
  "steps": [
    {"number": 1, "title": "src/main/java/com/example/CacheConfig.java", "status": "pending"},
    {"number": 2, "title": "src/main/java/com/example/CacheManager.java", "status": "pending"}
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
  "phase": "5-execute",
  "domain": "java",
  "profile": "module_testing",
  "type": "FIX",
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
    {"number": 1, "title": "src/test/java/com/example/CacheTest.java", "status": "pending"}
  ],
  "verification": {
    "commands": ["mvn test -Dtest=CacheTest"],
    "criteria": "Test passes",
    "manual": false
  },
  "current_step": 1
}
```

## Key Fields

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `id` | string | Yes | Unique task identifier (TASK-{SEQ}) |
| `title` | string | Yes | Task title for display |
| `domain` | string | Yes | Single domain from deliverable (java, javascript, plan-marshall-plugin-dev) |
| `profile` | string | Yes | Workflow profile (implementation, module_testing, integration_testing) |
| `skills` | list | Yes | Domain skills pre-resolved during task creation |
| `deliverable` | int | Yes | Referenced deliverable number (1:1 constraint) |
| `depends_on` | string | Yes | Task dependencies for ordering |
| `origin` | string | Yes | Task origin: `plan` or `fix` |
| `description` | string | Yes | Detailed task description |
| `steps` | table | Yes | File paths to process |
| `verification` | object | Yes | Commands and criteria |
| `priority` | string | No | Execution priority (fix tasks) |
| `finding` | object | No | Original finding details (fix tasks only) |

## Task ID Format

Tasks use sequential numbering with zero-padded format and type suffix:

| Format | Example | Description |
|--------|---------|-------------|
| `TASK-{SEQ}-{TYPE}` | `TASK-001-IMPL` | 3-digit sequence + type suffix |

### Task Types

| Type | Source | Description |
|------|--------|-------------|
| `IMPL` | plan phase | Implementation task from deliverable |
| `FIX` | finalize | Generic fix from finding |
| `SONAR` | finalize:sonar | Sonar issue fix |
| `PR` | finalize:pr | PR review comment fix |
| `LINT` | finalize:local | Lint/format fix |
| `SEC` | finalize:security | Security finding fix |
| `DOC` | finalize:doc | Documentation fix |

**Filename format**: `TASK-{SEQ}-{TYPE}.json` (e.g., `TASK-001-IMPL.json`, `TASK-003-FIX.json`)

## Origin Field

Indicates where task was created:

| Value | Meaning |
|-------|---------|
| `plan` | Created during task-plan phase from deliverable |
| `fix` | Created during finalize phase from finding |

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

The `domain` field is inherited from the deliverable:

| Domain | Description |
|--------|-------------|
| `java` | Java code |
| `javascript` | JavaScript code |
| `plan-marshall-plugin-dev` | Marketplace plugins |

### Profile Field

The `profile` field determines the workflow type:

| Profile | Description |
|---------|-------------|
| `implementation` | Create/modify production code |
| `testing` | Create/modify test code |
| `quality` | Documentation, verification |

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
                                     │ TASK-001-IMPL.json          │
                                     │ profile: implementation     │
                                     │ skills:                     │
                                     │   - pm-dev-java:java-core   │
                                     │   - pm-dev-java:java-cdi    │
                                     ├─────────────────────────────┤
                                     │ TASK-002-TEST.json          │
                                     │ profile: module_testing     │
                                     │ skills:                     │
                                     │   - pm-dev-java:java-core   │
                                     │   - pm-dev-java:junit-core  │
                                     │ depends: TASK-001-IMPL      │
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
| 1:N | One deliverable, multiple profiles | TASK-1-IMPL and TASK-2-TEST both have `deliverable: 1` |

### 1:N Pattern

When a deliverable has multiple profiles (implementation + module_testing), it creates multiple tasks - one per profile. Both tasks reference the same deliverable number:

- TASK-1-IMPL: `deliverable: 1`, `profile: implementation`
- TASK-2-TEST: `deliverable: 1`, `profile: module_testing`, `depends_on: ["TASK-1"]`

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
3. Consolidate verification commands
4. Generate steps from file lists
5. Compute task dependencies (testing depends on implementation)
6. Identify parallelizable tasks

**Constraint**: Each task maps to exactly one deliverable. No aggregation.

## Task Creation API

Uses stdin-based API with heredoc to avoid shell metacharacter issues:

```bash
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks add \
  --plan-id {plan_id} <<'EOF'
title: {task title}
deliverable: {deliverable_number}
domain: {domain}
profile: {profile}
skills:
  - pm-dev-java:java-core
  - pm-dev-java:java-cdi
phase: 5-execute
description: |
  {description from deliverable}

steps:
  - {file_1}
  - {file_2}
  - {file_3}

depends_on: TASK-001-IMPL

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
  parallel_group_1: [TASK-001-IMPL, TASK-003-IMPL]
  parallel_group_2: [TASK-002-IMPL]
  parallel_group_3: [TASK-004-IMPL]
  parallel_group_4: [TASK-005-IMPL]

lessons_recorded: {count}
```

## Steps Field Contract

**CRITICAL**: The `steps` field MUST contain file paths from the deliverable's `Affected files` section.

### Input Format (API calls)

When calling `manage-tasks add`, use YAML list format:

```yaml
steps:
  - marketplace/bundles/pm-workflow/agents/plan-init-agent.md
  - marketplace/bundles/pm-workflow/agents/solution-outline-agent.md
  - marketplace/bundles/pm-workflow/agents/task-plan-agent.md
```

### Stored Format (.json files)

The script converts input to JSON array format in task files:

```json
{
  "steps": [
    {"number": 1, "title": "marketplace/bundles/pm-workflow/agents/plan-init-agent.md", "status": "pending"},
    {"number": 2, "title": "marketplace/bundles/pm-workflow/agents/solution-outline-agent.md", "status": "pending"},
    {"number": 3, "title": "marketplace/bundles/pm-workflow/agents/task-plan-agent.md", "status": "pending"}
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
  - Update plan-init-agent to use TOON output
  - Migrate solution-outline-agent output format
  - Convert all remaining agents
```

**Why invalid:**
- Steps are action descriptions, not file paths
- Cannot track which files have been processed
- "all remaining agents" is vague
- Validation will reject this task
