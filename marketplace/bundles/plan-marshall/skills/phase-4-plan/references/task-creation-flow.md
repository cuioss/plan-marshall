# Phase 4: Task Creation Flow

Visual overview of the task creation workflow for human readers.

## 1:N Task Creation Flow

```
solution_outline.md                        TASK-*.toon (created by task-plan)
┌────────────────────────────┐             ┌────────────────────────────┐
│ **Metadata:**              │             │ TASK-001              │
│ - domain: java             │             │ profile: implementation    │
│ - module: auth-service     │  ───────►   │ skills: [java-core,        │
│                            │  (1:N)      │          java-cdi]         │
│ **Profiles:**              │             ├────────────────────────────┤
│ - implementation           │  ───────►   │ TASK-002              │
│ - module_testing           │             │ profile: module_testing    │
│                            │             │ skills: [java-core,        │
└────────────────────────────┘             │          junit-core]       │
                                           │ depends: TASK-001     │
                                           └────────────────────────────┘
```

## Terminal Step — Manifest Emission

After tasks are created and the execution order is computed, phase-4-plan
emits the per-plan **execution manifest** as the terminal step before phase
transition (SKILL.md Step 8b). The manifest is the single source of truth
that drives Phase 5's verification step selection and Phase 6's finalize-step
dispatch — phases 5 and 6 read it and obey, no per-doc skip logic remains in
their standards.

```
phase-4-plan
   │
   ├── Step 5..7: Create tasks (per-deliverable + holistic)
   ├── Step 8:    Compute execution order (parallel groups)
   │
   ├── Step 8b:   ┌────────────────────────────────────────────┐
   │              │  manage-execution-manifest compose         │
   │              │  inputs: change_type, track,               │
   │              │          scope_estimate, recipe_key,       │
   │              │          affected_files_count,             │
   │              │          phase-5/phase-6 candidate steps   │
   │              │  writes: .plan/local/plans/{plan_id}/      │
   │              │            execution.toon                  │
   │              │  logs:   one decision.log entry per fired  │
   │              │          rule (seven-row matrix)           │
   │              └────────────────────────────────────────────┘
   │                                │
   │                                ▼
   │              ┌────────────────────────────────────────────┐
   │              │  manage-execution-manifest validate        │
   │              │  fails phase loudly on schema / unknown    │
   │              │  step IDs                                  │
   │              └────────────────────────────────────────────┘
   │
   ├── Step 9:    Q-Gate (verifies created tasks)
   ├── Step 10:   Record lessons
   └── Step 11:   Phase transition → phase-5-execute
                                │
                                ▼
              phase-5-execute reads execution.toon for
              early_terminate + verification_steps;
              phase-6-finalize reads execution.toon for
              steps[]; both dispatch verbatim.
```

The seven-row decision matrix (early_terminate, recipe, docs_only,
tests_only, surgical_bug_fix / surgical_tech_debt, verification_no_files,
default) is documented in
`marketplace/bundles/plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md`.

## Output Structure

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
  parallel_group_1: [TASK-1, TASK-3]
  parallel_group_2: [TASK-2, TASK-4]

lessons_recorded: {count}
qgate_pending_count: {0 if no findings}
```
