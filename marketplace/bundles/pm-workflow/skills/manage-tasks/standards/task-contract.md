# Task Contract

Standard structure for tasks created by task-plan skills. Tasks represent committable units of work derived from deliverables with pre-resolved skills for 7-phase workflow execution.

## Purpose

Each task:

- References one or more deliverables (M:N relationship)
- Contains domain and profile for workflow routing
- Includes explicit skills array (pre-resolved during task creation)
- Includes verification criteria
- Specifies dependencies on other tasks (for ordering/parallelization)
- Results in exactly one commit
- Tracks origin (plan or fix) for finalize loop handling

## Task File Format (TOON)

### Regular Task (from plan phase)

```toon
id: TASK-001-IMPL
title: "Create CacheConfig class"
domain: java
profile: implementation
skills:
  - pm-dev-java:java-core
  - pm-dev-java:java-cdi
deliverables: [1]
depends_on: none
origin: plan

description: |
  Create CacheConfig class with Redis configuration...

steps[N]{number,title,status}:
1,src/main/java/com/example/CacheConfig.java,pending
2,src/main/java/com/example/CacheManager.java,pending

verification:
  commands:
    - mvn test -Dtest=CacheConfigTest
  criteria: All tests pass
```

### Fix Task (from finalize phase)

```toon
id: TASK-003-FIX
title: "Fix: Test failure in CacheTest"
domain: java
profile: module_testing
skills:
  - pm-dev-java:junit-core
  - pm-dev-java:java-core
deliverables: [1]
depends_on: TASK-002-IMPL
origin: fix
priority: high

description: |
  Fix test failure detected during verification.

finding:
  type: test_failure
  file: src/test/java/com/example/CacheTest.java
  line: 58
  message: "AssertionError: expected 5 but was 3"

steps[1]{number,title,status}:
1,src/test/java/com/example/CacheTest.java,pending

verification:
  commands:
    - mvn test -Dtest=CacheTest
  criteria: Test passes
```

## Key Fields

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `id` | string | Yes | Unique task identifier (TASK-{SEQ}) |
| `title` | string | Yes | Task title for display |
| `domain` | string | Yes | Single domain from deliverable (java, javascript, plan-marshall-plugin-dev) |
| `profile` | string | Yes | Workflow profile (implementation, testing, quality) |
| `skills` | list | Yes | Domain skills pre-resolved during task creation |
| `deliverables` | list | Yes | Referenced deliverable numbers |
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

**Filename format**: `TASK-{SEQ}-{TYPE}.toon` (e.g., `TASK-001-IMPL.toon`, `TASK-003-FIX.toon`)

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
                                     │ TASK-001-IMPL.toon          │
                                     │ profile: implementation     │
                                     │ skills:                     │
                                     │   - pm-dev-java:java-core   │
                                     │   - pm-dev-java:java-cdi    │
                                     ├─────────────────────────────┤
                                     │ TASK-002-TEST.toon          │
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

Tasks and deliverables have a **many-to-many relationship**:

| Pattern | Description | Example |
|---------|-------------|---------|
| 1:1 | One deliverable -> one task | Single-profile deliverable |
| N:1 | Multiple deliverables -> one task | Similar small changes (aggregation) |
| 1:N | One deliverable -> multiple tasks | Multiple profiles (implementation + testing) |

### When to Use Each Pattern

**1:1 (Keep separate)**:
- Large deliverables that form a coherent unit
- Single-file changes
- Deliverables with unique verification requirements

**N:1 (Aggregate)**:
- Same change_type
- Same domain and profile
- Same execution_mode (must be `automated`)
- No dependency between them
- Combined file count < 10

**1:N (Multiple profiles)**:
- Deliverable has multiple profiles (implementation + testing)
- Each profile becomes a separate task
- Testing task depends on implementation task

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

### Step 5: Create Optimized Tasks

For each deliverable, for each profile in deliverable.profiles:
1. Resolve skills from architecture: `module.skills_by_profile.{profile}`
2. Set `domain` from deliverable, `profile` from current iteration
3. Consolidate verification commands
4. Generate steps from file lists
5. Compute task dependencies (testing depends on implementation)
6. Identify parallelizable tasks

### Step 6: Log Optimization Decisions

Record why deliverables were grouped/split for audit trail.

## Optimization Decision Table

| Factor | Aggregate | Split | Keep |
|--------|-----------|-------|------|
| Same change_type | Y | | |
| Same domain and profile | Y | | |
| Combined files < 10 | Y | | |
| Same execution_mode | Y | | |
| Both depends: none | Y | | |
| One depends on other | N (NEVER) | | |
| execution_mode: mixed | | Y | |
| Different concerns | | Y | |
| File count > 15 | | Consider | |
| Large but coherent | | | Y |
| Single file | | | Y |

## Task Creation API

Uses stdin-based API with heredoc to avoid shell metacharacter issues:

```bash
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks add \
  --plan-id {plan_id} <<'EOF'
title: {aggregated title}
deliverables: [{n1}, {n2}, {n3}]
domain: {domain}
profile: {profile}
skills:
  - pm-dev-java:java-core
  - pm-dev-java:java-cdi
phase: 5-execute
description: |
  {combined description}

steps:
  - {file_1}
  - {file_2}
  - {file_3}

depends_on: TASK-001-IMPL, TASK-002-IMPL

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

optimization_summary:
  deliverables_processed: {N}
  tasks_created: {M}
  aggregations: {count of deliverable groups}
  splits: {count of split deliverables}
  parallelizable_groups: {count of independent task groups}

tasks_created[M]{id,title,deliverables,depends_on}:
TASK-001-IMPL,Update misc agents to TOON,[1 2 4],none
TASK-002-IMPL,Update pm-dev-java agents to TOON,[3],TASK-001-IMPL
TASK-003-IMPL,Update TOON documentation,[5],none
TASK-004-IMPL,Create verification script,[6],TASK-001-IMPL TASK-002-IMPL
TASK-005-IMPL,Measure token savings,[6],TASK-004-IMPL

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

### Stored Format (.toon files)

The script converts input to TOON tabular format in task files:

```toon
steps[3]{number,title,status}:
1,marketplace/bundles/pm-workflow/agents/plan-init-agent.md,pending
2,marketplace/bundles/pm-workflow/agents/solution-outline-agent.md,pending
3,marketplace/bundles/pm-workflow/agents/task-plan-agent.md,pending
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
