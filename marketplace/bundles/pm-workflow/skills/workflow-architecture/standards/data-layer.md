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
│  │   phase-1-init  phase-2-outline  phase-3-plan  phase-4-execute  phase-5-finalize │
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
│  │  │ config  │ │lifecycle│ │solution-      │ │  tasks  │ │  files  │  │  │
│  │  │         │ │         │ │outline        │ │         │ │         │  │  │
│  │  └────┬────┘ └────┬────┘ └───────┬───────┘ └────┬────┘ └────┬────┘  │  │
│  │       │           │               │             │            │       │  │
│  │       ▼           ▼               ▼             ▼            ▼       │  │
│  │  ┌─────────┐ ┌─────────┐ ┌───────────────┐ ┌─────────┐ ┌─────────┐  │  │
│  │  │ config  │ │ status  │ │  solution_    │ │ TASK-*  │ │ plan    │  │  │
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
│  │ manage-config         │ config.toon       │ Plan configuration       │  │
│  │                       │                   │ • domains array          │  │
│  │                       │                   │ • commit_strategy        │  │
│  │                       │                   │ • finalize settings      │  │
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
│  │ manage-tasks          │ TASK-*.toon       │ Task files               │  │
│  │                       │                   │ • add (create task)      │  │
│  │                       │                   │ • get (read task)        │  │
│  │                       │                   │ • next (get pending)     │  │
│  │                       │                   │ • step-done (mark step)  │  │
│  │                       │                   │                          │  │
│  ├───────────────────────┼───────────────────┼──────────────────────────┤  │
│  │                       │                   │                          │  │
│  │ manage-references     │ references.toon   │ External references      │  │
│  │                       │                   │ • branch name            │  │
│  │                       │                   │ • issue URL              │  │
│  │                       │                   │ • build system           │  │
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
│  │  # Read config                                                       │  │
│  │  python3 .plan/execute-script.py \                                   │  │
│  │    pm-workflow:manage-config:manage-config \                         │  │
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
│  │    pm-workflow:manage-lifecycle:manage-lifecycle \                   │  │
│  │    transition --plan-id my-feature --completed 1-init                │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## manage-config Commands

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                       MANAGE-CONFIG COMMANDS                                │
│                                                                             │
│  Script: pm-workflow:manage-config:manage-config                            │
│                                                                             │
│  ┌──────────────┬────────────────────────────┬──────────────────────────┐  │
│  │ COMMAND      │ PARAMETERS                 │ PURPOSE                  │  │
│  ├──────────────┼────────────────────────────┼──────────────────────────┤  │
│  │ create       │ --plan-id --domains        │ Create config.toon       │  │
│  │ read         │ --plan-id                  │ Read full config         │  │
│  │ get          │ --plan-id --field          │ Read single field        │  │
│  │ get-multi    │ --plan-id --fields         │ Read multiple fields     │  │
│  │ set          │ --plan-id --field --value  │ Set single field         │  │
│  └──────────────┴────────────────────────────┴──────────────────────────┘  │
│                                                                             │
│  config.toon STRUCTURE:                                                     │
│  ══════════════════════                                                     │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  domains: [java]                                                     │  │
│  │                                                                      │  │
│  │  commit_strategy: per_task                                           │  │
│  │  create_pr: true                                                     │  │
│  │  verification_required: true                                         │  │
│  │  verification_command: /pm-dev-builder:builder-build-and-fix         │  │
│  │  branch_strategy: feature                                            │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## manage-lifecycle Commands

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                     MANAGE-LIFECYCLE COMMANDS                               │
│                                                                             │
│  Script: pm-workflow:manage-lifecycle:manage-lifecycle                      │
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
│  │  current_phase: 4-execute                                            │  │
│  │                                                                      │  │
│  │  phases[5]{name,status}:                                             │  │
│  │  1-init,done                                                         │  │
│  │  2-outline,done                                                      │  │
│  │  3-plan,done                                                         │  │
│  │  4-execute,in_progress                                               │  │
│  │  5-finalize,pending                                                  │  │
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
│  ┌──────────────┬────────────────────────────┬──────────────────────────┐  │
│  │ COMMAND      │ PARAMETERS                 │ PURPOSE                  │  │
│  ├──────────────┼────────────────────────────┼──────────────────────────┤  │
│  │ add          │ --plan-id <<'EOF'...EOF    │ Create TASK-*.toon       │  │
│  │ get          │ --plan-id --task-number    │ Read task                │  │
│  │ next         │ --plan-id [--include-      │ Get next pending task    │  │
│  │              │ context]                   │                          │  │
│  │ step-done    │ --plan-id --task --step    │ Mark step complete       │  │
│  │ update-step  │ --plan-id --task-number    │ Update step status       │  │
│  │              │ --step-number --status     │                          │  │
│  │ update       │ --plan-id --task-number    │ Update task status       │  │
│  │              │ --status [--notes]         │                          │  │
│  └──────────────┴────────────────────────────┴──────────────────────────┘  │
│                                                                             │
│  TASK-*.toon STRUCTURE:                                                     │
│  ═══════════════════════                                                    │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  title: Implement UserService                                        │  │
│  │  deliverables: [1, 2]                                                │  │
│  │  domain: java                                                        │  │
│  │  profile: implementation                                             │  │
│  │  phase: 4-execute                                                    │  │
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
│  │       ├── config.toon        # Configuration (domains, settings)        │
│  │       ├── status.toon        # Lifecycle (phases, progress)             │
│  │       ├── request.md         # Original request                         │
│  │       ├── references.toon    # External refs (branch, issue)            │
│  │       ├── solution_outline.md# Deliverables                              │
│  │       ├── TASK-001.toon      # First task                               │
│  │       ├── TASK-002.toon      # Second task                              │
│  │       ├── work-log.log       # Execution log                            │
│  │       └── script-execution.log # Script invocation log                  │
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
| `pm-workflow:manage-config/SKILL.md` | Full config commands |
| `pm-workflow:manage-lifecycle/SKILL.md` | Full lifecycle commands |
| `pm-workflow:manage-tasks/SKILL.md` | Full task commands |
| `plan-marshall:manage-logging/SKILL.md` | Work log and script execution logging |
