# Task Plan Skill Contract

Workflow skill for plan phase - transforms solution outline deliverables into optimized, committable tasks.

**Implementation**: `pm-workflow:phase-refine-plan`

---

## Purpose

Task plan skills analyze solution outline deliverables and create optimized tasks. Each task represents a committable unit of work with explicit domain, profile, and pre-resolved skills fields.

**Flow**: Solution Outline (Deliverables) → Tasks with pre-resolved skills

---

## Invocation

**Phase**: `plan`

**Agent invocation**:
```bash
plan-phase-agent plan_id={plan_id} phase=plan
```

**Skill resolution**:
```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  resolve-workflow-skill --phase plan
```

Result:
```toon
status: success
domain: system
phase: plan
workflow_skill: pm-workflow:phase-refine-plan
```

---

## Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |

## Workflow Skill Responsibilities

The workflow skill autonomously:

1. **Loads deliverables**: From solution_outline.md
2. **Builds dependency graph**: From deliverable `depends` fields
3. **Analyzes for optimization**: Aggregation and split decisions
4. **Inherits skills**: From deliverable.skills (set during solution-outline)
5. **Creates tasks**: With explicit `domain`, `profile`, `skills`

```
Workflow Skill Execution:
┌──────────────────────────────────────────────────────────────────┐
│ 1. Load deliverables via manage-solution-outline                 │
│ 2. Build dependency graph from deliverable.depends               │
│ 3. Analyze for aggregation/split                                 │
│ 4. For each task:                                                │
│    a. Inherit skills from deliverable.skills                     │
│    b. Create task with domain, profile, skills                   │
│ 5. Write tasks via manage-tasks add                              │
└──────────────────────────────────────────────────────────────────┘
```

---

## Skills Inheritance

Skills are inherited from deliverables (which get them from module.skills_by_profile during solution-outline):

```
solution_outline.md                      TASK-001.toon
┌──────────────────────────────────────┐ ┌──────────────────────────────────────┐
│ ### 1. Create CacheConfig class      │ │ domain: java          ← Inherited   │
│ **Metadata:**                        │ │ profile: implementation ← Inherited │
│ - domain: java                       │ │ skills:                 ← Inherited │
│ - profile: implementation            │ │   - pm-dev-java:java-core            │
│ - skills: [java-core, java-cdi]      │ │   - pm-dev-java:java-cdi             │
└──────────────────────────────────────┘ └──────────────────────────────────────┘
                     ↓ task-plan inherits domain/profile/skills
```

---

## Key Responsibilities

Apply optimization to package deliverables efficiently while maintaining:

1. **Atomic committability**: Each task = one coherent commit
2. **Testability**: Each task has verification
3. **Execution efficiency**: Minimize agent spawns and skill loads
4. **Dependency ordering**: Tasks execute in valid dependency order
5. **Parallelization**: Independent tasks can run concurrently
6. **Skill pre-resolution**: Each task gets pre-resolved skills array for execution

## Optimization Workflow

Task-plan skills MUST follow the 6-step optimization workflow:

### Step 1: Load All Deliverables

```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline list-deliverables \
  --plan-id {plan_id}
```

Extract for each deliverable:
- `metadata.change_type`
- `metadata.execution_mode`
- `metadata.domain`
- `metadata.profile`
- `metadata.depends`
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
- `execution_mode: mixed` → MUST split
- Different concerns → SHOULD split
- File count > 15 → CONSIDER splitting

### Step 5: Create Optimized Tasks

For each task:
1. Inherit skills from deliverable(s) - copy `deliverable.skills` to `task.skills`
2. Set `domain` and `profile` from deliverable
3. Consolidate verification commands
4. Generate steps from file lists
5. Compute task dependencies from deliverable dependencies
6. Identify parallelizable tasks

### Step 6: Log Optimization Decisions

Record why deliverables were grouped/split for audit trail.

> **Full Decision Tables**: See [task-contract.md](../../manage-tasks/standards/task-contract.md) for optimization decision tables and dependency rules.

## Task Creation

Uses stdin-based API with heredoc to avoid shell metacharacter issues:

```bash
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks add \
  --plan-id {plan_id} <<'EOF'
title: {aggregated title}
deliverables: [{n1}, {n2}, {n3}]
domain: {domain}
profile: {profile}
skills:
  - {bundle}:{skill1}
  - {bundle}:{skill2}
phase: execute
description: |
  {combined description}

steps:
  - {file_1}
  - {file_2}
  - {file_3}

origin: plan
depends_on: TASK-001, TASK-002

verification:
  commands:
    - {cmd1}
    - {cmd2}
  criteria: {criteria}
EOF
```

## Return Structure

```toon
status: success|error
plan_id: {plan_id}

optimization_summary:
  deliverables_processed: {N}
  tasks_created: {M}
  aggregations: {count of deliverable groups}
  splits: {count of split deliverables}
  parallelizable_groups: {count of independent task groups}

tasks_created[M]{id,title,deliverables,depends_on}:
TASK-001,Update misc agents to TOON,[1 2 4],none
TASK-002,Update pm-dev-java agents to TOON,[3],TASK-001
TASK-003,Update TOON documentation,[5],none

execution_order:
  parallel_group_1: [TASK-001, TASK-003]
  parallel_group_2: [TASK-002]

lessons_recorded: {count}
message: {error message if status=error}
```

## Skill Inheritance

Skills are inherited from deliverables:

| Source | Description |
|--------|-------------|
| `deliverable.skills` | Set during solution-outline from module.skills_by_profile |

Task-plan copies skills directly from deliverable(s) to task. No resolution API call needed.

## Error Handling

| Scenario | Action |
|----------|--------|
| Solution outline not found | Return `{status: error, message: "Solution outline not found"}` |
| Circular dependencies | Reject deliverables, return error with cycle |
| Invalid domain | Return error with valid domains |
| Script execution fails | Record lesson-learned, return error |

## Integration

**Callers**: `pm-workflow:phase-refine-plan-agent` (thin agent)

**Data Layer**:
- `pm-workflow:manage-solution-outline:manage-solution-outline` - Solution outline queries, deliverable skills
- `pm-workflow:manage-tasks:manage-tasks` - Task creation with deliverable references

**Prerequisites**: [Solution Outline Skill](solution-outline-skill-contract.md) completion and [User Review Protocol](user-review-protocol.md) approval

---

## Related Documents

- [solution-outline-skill-contract.md](solution-outline-skill-contract.md) - Previous phase (outline)
- [task-execution-skill-contract.md](task-execution-skill-contract.md) - Next phase (execute)
- [task-contract.md](../../manage-tasks/standards/task-contract.md) - Task structure and optimization rules
- [deliverable-contract.md](../../manage-solution-outline/standards/deliverable-contract.md) - Deliverable structure
- [user-review-protocol.md](user-review-protocol.md) - Approval gate before plan phase
