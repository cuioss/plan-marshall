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
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────────┐ ┌─────────┐ ┌─────────┐  │
│  │  │ manage- │ │ manage- │ │ manage- │ │   manage-     │ │ manage- │ │ manage- │  │
│  │  │referenc.│ │ status  │ │lifecycle│ │solution-      │ │  tasks  │ │  files  │  │
│  │  │         │ │         │ │         │ │outline        │ │         │ │         │  │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └───────┬───────┘ └────┬────┘ └────┬────┘  │
│  │       │           │           │               │             │            │       │
│  │       ▼           ▼           ▼               ▼             ▼            ▼       │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────────┐ ┌─────────┐ ┌─────────┐  │
│  │  │referenc.│ │ status  │ │ phase   │ │  solution_    │ │ TASK-*  │ │ plan    │  │
│  │  │ .json   │ │ .json   │ │ routing │ │  outline.md   │ │ .json   │ │directory│  │
│  │  └─────────┘ └─────────┘ └─────────┘ └───────────────┘ └─────────┘ └─────────┘  │
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
│  │ manage-assessments    │ assessments.jsonl │ Component evaluations    │  │
│  │                       │                   │ • add (certainty/conf.)  │  │
│  │                       │                   │ • query (with filters)   │  │
│  │                       │                   │ • clear (all or agent)   │  │
│  │                       │                   │                          │  │
│  ├───────────────────────┼───────────────────┼──────────────────────────┤  │
│  │                       │                   │                          │  │
│  │ manage-findings       │ findings.jsonl    │ Findings + Q-Gate        │  │
│  │                       │ qgate-{phase}     │ • add/query/resolve      │  │
│  │                       │   .jsonl          │ • promote (findings)     │  │
│  │                       │                   │ • qgate add/query/clear  │  │
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

## Command References

For full command details, see each manage-* skill's SKILL.md. Key scripts:

| Skill | Script Notation | Purpose |
|-------|-----------------|---------|
| `manage-status` | `plan-marshall:manage-status:manage_status` | Phase tracking, metadata, plan discovery |
| `manage-lifecycle` | `plan-marshall:manage-lifecycle:manage-lifecycle` | Phase transitions, plan listing, archiving |
| `manage-tasks` | `plan-marshall:manage-tasks:manage-tasks` | Task CRUD, step tracking, status updates |
| `manage-references` | `plan-marshall:manage-references:manage-references` | Plan refs (domains, branch, issue) |
| `manage-solution-outline` | `plan-marshall:manage-solution-outline:manage-solution-outline` | Solution document write/read/validate |
| `manage-plan-documents` | `plan-marshall:manage-plan-documents:manage-plan-documents` | Request and typed document management |
| `manage-files` | `plan-marshall:manage-files:manage-files` | Directory operations, plan deletion |
| `manage-findings` | `plan-marshall:manage-findings:manage-findings` | Findings, Q-Gate, assessments |
| `manage-logging` | `plan-marshall:manage-logging:manage-logging` | Work log, decision log, script log |
| `manage-config` | `plan-marshall:manage-config:manage-config` | Marshal.json project configuration |
| `manage-architecture` | `plan-marshall:manage-architecture:architecture` | Module analysis, skill resolution |
| `manage-assessments` | `plan-marshall:manage-assessments:manage-assessments` | Component evaluations |
| `manage-metrics` | `plan-marshall:manage-metrics:manage-metrics` | Plan metrics collection |

For file formats (status.json, TASK-*.json, references.json, etc.), see [artifacts.md](artifacts.md).

---

## File Access Rules

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                       FILE ACCESS RULES                                     │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  .plan/ FILES                         PROJECT FILES                  │  │
│  │  ════════════                         ═════════════                  │  │
│  │                                                                      │  │
│  │  PASS Access via execute-script.py       PASS Access via Read/Write/Edit  │  │
│  │  ✗ Direct Read/Write/Edit             PASS Access via Glob/Grep        │  │
│  │  ✗ cat/head/tail/ls                   PASS Access via Bash             │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  WHY SCRIPT-ONLY ACCESS?                                                    │
│  ═══════════════════════                                                    │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  1. PERMISSIONS                                                      │  │
│  │     • Execute-script.py has pre-approved permissions                 │  │
│  │     • Direct file access triggers permission prompts                 │  │
│  │                                                                      │  │
│  │  2. VALIDATION                                                       │  │
│  │     • Scripts validate input/output                                  │  │
│  │     • Ensures consistent file format                                 │  │
│  │                                                                      │  │
│  │  3. LOGGING                                                          │  │
│  │     • Scripts log to execution log                                   │  │
│  │     • Enables debugging and auditing                                 │  │
│  │                                                                      │  │
│  │  4. ABSTRACTION                                                      │  │
│  │     • File format changes don't break consumers                      │  │
│  │     • Single point of maintenance                                    │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Plan Directory Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                     PLAN DIRECTORY STRUCTURE                                │
│                                                                             │
│  .plan/                                                                     │
│  ├── execute-script.py          # Script executor                           │
│  ├── plans/                     # Active plans                              │
│  │   └── {plan_id}/                                                         │
│  │       ├── status.json        # Lifecycle (phases, progress, metadata)   │
│  │       ├── request.md         # Original request                         │
│  │       ├── references.json    # Plan refs & config (domains, branch, issue) │
│  │       ├── solution_outline.md# Deliverables                              │
│  │       ├── artifacts/          # Plan-level artifacts                    │
│  │       │   ├── assessments.jsonl      # Component assessments          │
│  │       │   ├── findings.jsonl         # Unified findings               │
│  │       │   └── qgate-{phase}.jsonl    # Per-phase Q-Gate findings      │
│  │       ├── work/              # Working files (outline phase+)           │
│  │       ├── tasks/             # Task files                               │
│  │       │   ├── TASK-001.json                                             │
│  │       │   └── TASK-002.json                                             │
│  │       └── logs/              # Execution logs                           │
│  │           ├── work.log                                                   │
│  │           ├── decision.log                                               │
│  │           └── script-execution.log                                       │
│  │                                                                          │
│  ├── archived-plans/            # Completed plans                          │
│  │   └── {date}-{plan_id}/                                                  │
│  │                                                                          │
│  └── temp/                      # Temporary files                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [artifacts.md](artifacts.md) | Plan file formats in detail |
| [phases.md](phases.md) | Which phase uses which files |
| `plan-marshall:manage-references/SKILL.md` | Full references commands |
| `plan-marshall:manage-status/SKILL.md` | Full status commands |
| `plan-marshall:manage-lifecycle/SKILL.md` | Full lifecycle commands |
| `plan-marshall:manage-tasks/SKILL.md` | Full task commands |
| `plan-marshall:manage-logging/SKILL.md` | Work log and script execution logging |
