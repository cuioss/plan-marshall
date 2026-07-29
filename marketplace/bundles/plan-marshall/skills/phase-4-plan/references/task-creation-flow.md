# Phase 4: Task Creation Flow

Visual overview of the task creation workflow for human readers.

## 1:N Task Creation Flow

```text
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

```text
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
   │              │          phase-5-execute/phase-6-finalize candidate steps   │
   │              │  writes: .plan/local/plans/{plan_id}/      │
   │              │            execution.toon                  │
   │              │  logs:   one decision.log entry per fired  │
   │              │          rule (six-row matrix)             │
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

The six-row decision matrix (early_terminate, recipe, tests_only,
surgical_bug_fix / surgical_tech_debt, verification_no_files,
default) is documented in
`marketplace/bundles/plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md`.

## Output Structure

The phase return TOON contract is owned by `../SKILL.md` § Step 10 "Output" — see
that block for the authoritative field set. It is deliberately not restated here:
this document is a human-readable flow overview, and a second copy of the contract
drifts from the first the moment a field is added to one and not the other.
