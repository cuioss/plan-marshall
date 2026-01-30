# Data Layer (manage-* Skills)

The pm-workflow bundle uses manage-* skills as the data access layer for all plan files.

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
│  │   phase-1-init  phase-2-refine  phase-3-outline  phase-4-plan  phase-5-execute  phase-6-verify  phase-7-finalize │
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
│  │  ┌─────────┐ ┌─────────┐ ┌───────────────┐ ┌─────────┐ ┌─────────┐  │  │
│  │  │ manage- │ │ manage- │ │   manage-     │ │ manage- │ │ manage- │  │  │
│  │  │referenc.│ │lifecycle│ │solution-      │ │  tasks  │ │  files  │  │  │
│  │  │         │ │         │ │outline        │ │         │ │         │  │  │
│  │  └────┬────┘ └────┬────┘ └───────┬───────┘ └────┬────┘ └────┬────┘  │  │
│  │       │           │               │             │            │       │  │
│  │       ▼           ▼               ▼             ▼            ▼       │  │
│  │  ┌─────────┐ ┌─────────┐ ┌───────────────┐ ┌─────────┐ ┌─────────┐  │  │
│  │  │referenc.│ │ status  │ │  solution_    │ │ TASK-*  │ │ plan    │  │  │
│  │  │ .toon   │ │ .toon   │ │  outline.md   │ │ .toon   │ │directory│  │  │
│  │  └─────────┘ └─────────┘ └───────────────┘ └─────────┘ └─────────┘  │  │
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
│  │ manage-lifecycle      │ status.toon       │ Plan lifecycle           │  │
│  │                       │                   │ • current phase          │  │
│  │                       │                   │ • phase statuses         │  │
│  │                       │                   │ • phase transitions      │  │
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
│  │ manage-references     │ references.toon   │ Plan references & config │  │
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
│  │    pm-workflow:manage-references:manage-references \                 │  │
│  │    read --plan-id my-feature                                         │  │
│  │                                                                      │  │
│  │  # Create task                                                       │  │
│  │  python3 .plan/execute-script.py \                                   │  │
│  │    pm-workflow:manage-tasks:manage-tasks \                           │  │
│  │    add --plan-id my-feature <<'EOF'                                  │  │
│  │  title: Implement feature                                            │  │
│  │  domain: java                                                        │  │
│  │  profile: implementation                                             │  │
│  │  ...                                                                 │  │
│  │  EOF                                                                 │  │
│  │                                                                      │  │
│  │  # Transition phase                                                  │  │
│  │  python3 .plan/execute-script.py \                                   │  │
│  │    pm-workflow:plan-marshall:manage-lifecycle \                   │  │
│  │    transition --plan-id my-feature --completed 1-init                │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

---

## manage-lifecycle Commands

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                     MANAGE-LIFECYCLE COMMANDS                               │
│                                                                             │
│  Script: pm-workflow:plan-marshall:manage-lifecycle                      │
│                                                                             │
│  ┌────────────────────┬─────────────────────────┬────────────────────────┐ │
│  │ COMMAND            │ PARAMETERS              │ PURPOSE                │ │
│  ├────────────────────┼─────────────────────────┼────────────────────────┤ │
│  │ create             │ --plan-id --title       │ Create status.toon     │ │
│  │                    │ --phases                │                        │ │
│  │ read               │ --plan-id               │ Read full status       │ │
│  │ progress           │ --plan-id               │ Get progress %         │ │
│  │ transition         │ --plan-id --completed   │ Move to next phase     │ │
│  │ set-phase          │ --plan-id --phase       │ Set current phase      │ │
│  │ route              │ --phase                 │ Get skill for phase    │ │
│  │ get-routing-context│ --plan-id               │ Phase + skill + prog   │ │
│  │ list               │ [--filter]              │ List all plans         │ │
│  │ archive            │ --plan-id               │ Archive completed      │ │
│  └────────────────────┴─────────────────────────┴────────────────────────┘ │
│                                                                             │
│  status.toon STRUCTURE:                                                     │
│  ═══════════════════════                                                    │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  title: Implement JWT Authentication                                 │  │
│  │  current_phase: 5-execute                                            │  │
│  │                                                                      │  │
│  │  phases[7]{name,status}:                                             │  │
│  │  1-init,done                                                         │  │
│  │  2-refine,done                                                       │  │
│  │  3-outline,done                                                      │  │
│  │  4-plan,done                                                         │  │
│  │  5-execute,in_progress                                               │  │
│  │  6-verify,pending                                                    │  │
│  │  7-finalize,pending                                                  │  │
│  │                                                                      │  │
│  │  created: 2025-12-02T10:00:00Z                                       │  │
│  │  updated: 2025-12-02T14:30:00Z                                       │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## manage-tasks Commands

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                       MANAGE-TASKS COMMANDS                                 │
│                                                                             │
│  Script: pm-workflow:manage-tasks:manage-tasks                              │
│                                                                             │
│  ┌───────────────┬───────────────────────────┬──────────────────────────┐  │
│  │ COMMAND       │ PARAMETERS                │ PURPOSE                  │  │
│  ├───────────────┼───────────────────────────┼──────────────────────────┤  │
│  │ add           │ --plan-id <<'EOF'...EOF   │ Create TASK-*.json       │  │
│  │ get           │ --plan-id --number        │ Read task                │  │
│  │ next          │ --plan-id [--include-     │ Get next pending task    │  │
│  │               │ context]                  │                          │  │
│  │ finalize-step │ --plan-id --task --step   │ Mark step done/skipped   │  │
│  │               │ --outcome [--reason]      │                          │  │
│  │ update        │ --plan-id --number        │ Update task status       │  │
│  │               │ --status                  │                          │  │
│  └───────────────┴───────────────────────────┴──────────────────────────┘  │
│                                                                             │
│  TASK-*.json STRUCTURE:                                                     │
│  ═══════════════════════                                                    │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  title: Implement UserService                                        │  │
│  │  deliverable: 1                                                      │  │
│  │  domain: java                                                        │  │
│  │  profile: implementation                                             │  │
│  │  phase: 5-execute                                                    │  │
│  │  status: pending                                                     │  │
│  │                                                                      │  │
│  │  description: |                                                      │  │
│  │    Create UserService with CRUD operations                           │  │
│  │                                                                      │  │
│  │  steps:                                                              │  │
│  │    - src/main/java/com/example/UserService.java                      │  │
│  │    - src/main/java/com/example/UserRepository.java                   │  │
│  │                                                                      │  │
│  │  depends_on: []                                                      │  │
│  │                                                                      │  │
│  │  skills:                                                             │  │
│  │    - pm-dev-java:java-core                                           │  │
│  │    - pm-dev-java:java-cdi                                            │  │
│  │                                                                      │  │
│  │  verification:                                                       │  │
│  │    commands:                                                         │  │
│  │      - mvn test -pl user-service                                     │  │
│  │    criteria: All tests pass                                          │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

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
│  │  ✓ Access via execute-script.py       ✓ Access via Read/Write/Edit  │  │
│  │  ✗ Direct Read/Write/Edit             ✓ Access via Glob/Grep        │  │
│  │  ✗ cat/head/tail/ls                   ✓ Access via Bash             │  │
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
│  │       ├── status.toon        # Lifecycle (phases, progress)             │
│  │       ├── request.md         # Original request                         │
│  │       ├── references.toon    # Plan refs & config (domains, branch, issue) │
│  │       ├── solution_outline.md# Deliverables                              │
│  │       ├── work/              # Working files (outline phase+)           │
│  │       ├── tasks/             # Task files                               │
│  │       │   ├── TASK-001-IMPL.json                                        │
│  │       │   └── TASK-002-IMPL.json                                        │
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
| `pm-workflow:manage-references/SKILL.md` | Full references commands |
| `pm-workflow:plan-marshall/SKILL.md` | Full lifecycle commands |
| `pm-workflow:manage-tasks/SKILL.md` | Full task commands |
| `plan-marshall:manage-logging/SKILL.md` | Work log and script execution logging |
