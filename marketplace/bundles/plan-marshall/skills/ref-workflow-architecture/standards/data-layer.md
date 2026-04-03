# Data Layer (manage-* Skills)

The plan-marshall bundle uses manage-* skills as the data access layer for all plan files.

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                          DATA LAYER ARCHITECTURE                            │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │   WORKFLOW SKILLS                                                    │  │
│  │   ═══════════════                                                    │  │
│  │   phase-1-init  phase-2-refine  phase-3-outline  phase-4-plan  phase-5-execute  phase-6-finalize │
│  │       │           │               │            │             │       │  │
│  │       │           │               │            │             │       │  │
│  │       ▼           ▼               ▼            ▼             ▼       │  │
│  │  ┌──────────────────────────────────────────────────────────────┐   │  │
│  │  │                                                              │   │  │
│  │  │                    execute-script.py                         │   │  │
│  │  │                    ═════════════════                         │   │  │
│  │  │                                                              │   │  │
│  │  └──────────────────────────────────────────────────────────────┘   │  │
│  │       │           │               │            │             │       │  │
│  │       ▼           ▼               ▼            ▼             ▼       │  │
│  │  ┌─────────┐ ┌─────────┐ ┌───────────────┐ ┌─────────┐ ┌─────────┐  │
│  │  │ manage- │ │ manage- │ │   manage-     │ │ manage- │ │ manage- │  │
│  │  │referenc.│ │ status  │ │solution-      │ │  tasks  │ │  files  │  │
│  │  │         │ │         │ │outline        │ │         │ │         │  │
│  │  └────┬────┘ └────┬────┘ └───────┬───────┘ └────┬────┘ └────┬────┘  │
│  │       │           │               │             │            │       │
│  │       ▼           ▼               ▼             ▼            ▼       │
│  │  ┌─────────┐ ┌─────────┐ ┌───────────────┐ ┌─────────┐ ┌─────────┐  │
│  │  │referenc.│ │ status  │ │  solution_    │ │ TASK-*  │ │ plan    │  │
│  │  │ .json   │ │ .json   │ │  outline.md   │ │ .json   │ │directory│  │
│  │  └─────────┘ └─────────┘ └───────────────┘ └─────────┘ └─────────┘  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## manage-* Skill Inventory

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                       MANAGE-* SKILL INVENTORY                              │
│                                                                             │
│  ┌───────────────────────┬───────────────────┬──────────────────────────┐  │
│  │ SKILL                 │ FILE              │ PURPOSE                  │  │
│  ├───────────────────────┼───────────────────┼──────────────────────────┤  │
│  │                       │                   │                          │  │
│  ├───────────────────────┼───────────────────┼──────────────────────────┤  │
│  │                       │                   │                          │  │
│  │ manage-status         │ status.json       │ Plan status              │  │
│  │                       │                   │ • current phase          │  │
│  │                       │                   │ • phase statuses         │  │
│  │                       │                   │ • metadata               │  │
│  │                       │                   │                          │  │
│  ├───────────────────────┼───────────────────┼──────────────────────────┤  │
│  │                       │                   │                          │  │
│  │ manage-status         │ (phase routing)   │ Plan lifecycle           │  │
│  │   (lifecycle ops)     │                   │ • phase transitions      │  │
│  │                       │                   │ • phase routing          │  │
│  │                       │                   │ • plan discovery         │  │
│  │                       │                   │                          │  │
│  ├───────────────────────┼───────────────────┼──────────────────────────┤  │
│  │                       │                   │                          │  │
│  │ manage-plan-documents │ request.md        │ Typed documents          │  │
│  │                       │                   │ • request creation       │  │
│  │                       │                   │ • document templates     │  │
│  │                       │                   │                          │  │
│  ├───────────────────────┼───────────────────┼──────────────────────────┤  │
│  │                       │                   │                          │  │
│  │ manage-solution-      │ solution_         │ Solution document        │  │
│  │ outline               │ outline.md        │ • write (with validate)  │  │
│  │                       │                   │ • list-deliverables      │  │
│  │                       │                   │ • get-module-context     │  │
│  │                       │                   │                          │  │
│  ├───────────────────────┼───────────────────┼──────────────────────────┤  │
│  │                       │                   │                          │  │
│  │ manage-tasks          │ TASK-*.json       │ Task files               │  │
│  │                       │                   │ • add (create task)      │  │
│  │                       │                   │ • get (read task)        │  │
│  │                       │                   │ • next (get pending)     │  │
│  │                       │                   │ • finalize-step (mark)   │  │
│  │                       │                   │                          │  │
│  ├───────────────────────┼───────────────────┼──────────────────────────┤  │
│  │                       │                   │                          │  │
│  │ manage-references     │ references.json   │ Plan references & config │  │
│  │                       │                   │ • domains array          │  │
│  │                       │                   │ • branch name            │  │
│  │                       │                   │ • issue URL              │  │
│  │                       │                   │                          │  │
│  ├───────────────────────┼───────────────────┼──────────────────────────┤  │
│  │                       │                   │                          │  │
│  │ manage-files          │ directory         │ Directory operations     │  │
│  │                       │                   │ • create-or-reference    │  │
│  │                       │                   │ • delete-plan            │  │
│  │                       │                   │                          │  │
│  ├───────────────────────┼───────────────────┼──────────────────────────┤  │
│  │                       │                   │                          │  │
│  │ manage-findings       │ findings.jsonl    │ Findings + Q-Gate +      │  │
│  │                       │ assessments.jsonl │ Assessments              │  │
│  │                       │ qgate-{phase}     │ • add/query/resolve      │  │
│  │                       │   .jsonl          │ • promote (findings)     │  │
│  │                       │                   │ • qgate add/query/clear  │  │
│  │                       │                   │ • assessment add/query   │  │
│  │                       │                   │                          │  │
│  └───────────────────────┴───────────────────┴──────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Script Invocation Pattern

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                      SCRIPT INVOCATION PATTERN                              │
│                                                                             │
│  ALL plan file access uses this pattern:                                    │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  python3 .plan/execute-script.py                                     │  │
│  │    {bundle}:{skill}:{script}                                         │  │
│  │    {subcommand}                                                      │  │
│  │    --plan-id {plan_id}                                               │  │
│  │    [additional args]                                                 │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  EXAMPLES:                                                                  │
│  ═════════                                                                  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  # Read references                                                    │  │
│  │  python3 .plan/execute-script.py \                                   │  │
│  │    plan-marshall:manage-references:manage-references \                 │  │
│  │    read --plan-id my-feature                                         │  │
│  │                                                                      │  │
│  │  # Create task                                                       │  │
│  │  python3 .plan/execute-script.py \                                   │  │
│  │    plan-marshall:manage-tasks:manage-tasks \                           │  │
│  │    add --plan-id my-feature <<'EOF'                                  │  │
│  │  title: Implement feature                                            │  │
│  │  domain: java                                                        │  │
│  │  profile: implementation                                             │  │
│  │  ...                                                                 │  │
│  │  EOF                                                                 │  │
│  │                                                                      │  │
│  │  # Create status                                                     │  │
│  │  python3 .plan/execute-script.py \                                   │  │
│  │    plan-marshall:manage-status:manage_status \                         │  │
│  │    create --plan-id my-feature --title "Title" --phases 1-init,...   │  │
│  │                                                                      │  │
│  │  # Transition phase                                                  │  │
│  │  python3 .plan/execute-script.py \                                   │  │
│  │    plan-marshall:manage-status:manage_status \                            │  │
│  │    transition --plan-id my-feature --completed 1-init                │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

For full command details and script notations, see each manage-* skill's SKILL.md. For file formats, see [artifacts.md](artifacts.md). For file access rules and enforcement, see [manage-contract.md](manage-contract.md).

---

## Plan Directory Structure

See [artifacts.md — Plan Directory Structure](artifacts.md#plan-directory-structure) for the canonical directory tree.

---

## Dependency Graph

```
manage-config (configuration authority)
├── manage-architecture (reads skill_domains for module resolution)
│   └── manage-solution-outline (primary consumer of architecture data)
├── manage-solution-outline (validates domains against config)
│   └── manage-tasks (deliverables → tasks 1:N mapping)
├── manage-tasks (inherits domain/profile from deliverables)
├── manage-status (routes phases using config workflow_skills)
│   └── manage-metrics (parallels phase transitions with timing)
├── manage-run-config (reads retention from marshal.json for cleanup)
└── manage-memories (reads retention from marshal.json for cleanup)

manage-findings
└── manage-lessons (promotion: findings → lessons)

manage-logging (independent, fire-and-forget)
manage-files (low-level utility, used by other manage-* skills)
manage-references (independent plan metadata)
manage-plan-documents (independent request storage)
```

---

## Data Flow Through Phases

```
Phase 1 (init):
  manage-status create → manage-references create → manage-plan-documents request create

Phase 2 (refine):
  manage-plan-documents request clarify

Phase 3 (outline):
  manage-architecture → manage-solution-outline write

Phase 4 (plan):
  manage-solution-outline list-deliverables → manage-tasks add (per deliverable)

Phase 5 (execute):
  manage-tasks next → [execute task] → manage-tasks finalize-step
  manage-findings add (during verification)

Phase 6 (finalize):
  manage-findings qgate add → manage-findings promote → manage-lessons add
  manage-metrics generate → manage-status archive
```

---

## Shared Infrastructure

All manage-* skills share:

| Component | Source | Purpose |
|-----------|--------|---------|
| `file_ops` | Shared Python module | Path resolution, JSON I/O, TOON output, timestamps |
| `input_validation` | Shared Python module | Plan ID validation, field type checks |
| `toon_parser` | Shared Python module | TOON serialization/deserialization |
| `constants` | Shared Python module | Phase names, Q-Gate phases, valid resolutions |
| [manage-contract.md](manage-contract.md) | This bundle | Shared contract, formats, error codes |
| `ref-toon-format` | This bundle | TOON format specification |

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [artifacts.md](artifacts.md) | Plan file formats in detail |
| [phases.md](phases.md) | Which phase uses which files |
| [manage-contract.md](manage-contract.md) | Shared contract, formats, error codes |
