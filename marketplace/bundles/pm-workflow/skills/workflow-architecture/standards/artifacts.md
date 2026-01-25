# Plan Artifacts

File formats and structures for plan data storage.

## Plan Directory Structure

```
.plan/plans/{plan_id}/
│
├── config.toon              Phase: init
├── status.toon              Phase: init
├── request.md               Phase: init
├── references.toon          Phase: init (optional)
│
├── solution_outline.md      Phase: outline
│
├── work/                    Phase: outline+ (working files)
│   ├── inventory_raw.toon       Raw inventory from scan
│   └── inventory_filtered.toon  Filtered/transformed inventory
│
├── tasks/                   Phase: plan
│   ├── TASK-001-IMPL.toon
│   ├── TASK-002-IMPL.toon
│   └── TASK-003-FIX.toon
│
└── logs/                    Phase: all (logging)
    ├── work.log                 Semantic progress tracking
    ├── decision.log             Decision entries
    └── script-execution.log     Technical script tracing
```

---

## Artifact Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INIT PHASE                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ config.toon  │  │ status.toon  │  │ request.md   │               │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤               │
│  │ domains      │  │ title        │  │ description  │               │
│  │ commit_strat │  │ current_phase│  │ context      │               │
│  │ create_pr    │  │ phases table │  │ constraints  │               │
│  │ branch_strat │  │ timestamps   │  │              │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                       OUTLINE PHASE                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                   solution_outline.md                        │    │
│  ├─────────────────────────────────────────────────────────────┤    │
│  │  ## Summary                                                  │    │
│  │  ## Overview (ASCII diagram)                                 │    │
│  │  ## Deliverables                                             │    │
│  │    ### 1. Title                                              │    │
│  │      Metadata: domain, module, change_type, depends          │    │
│  │      Profiles: implementation, testing                       │    │
│  │      Affected files, Verification, Success criteria          │    │
│  │    ### 2. Title                                              │    │
│  │      ...                                                     │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  work/                                                               │
│  ┌──────────────────────┐  ┌───────────────────────┐                │
│  │ inventory_raw.toon   │  │ inventory_filtered    │                │
│  ├──────────────────────┤  ├───────────────────────┤                │
│  │ Raw scan output      │  │ Transformed paths     │                │
│  │ from marketplace     │  │ grouped by type       │                │
│  └──────────────────────┘  └───────────────────────┘                │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                        PLAN PHASE                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  tasks/                                                              │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐     │
│  │ TASK-001-IMPL    │ │ TASK-002-IMPL    │ │ TASK-003-FIX     │     │
│  ├──────────────────┤ ├──────────────────┤ ├──────────────────┤     │
│  │ title, status    │ │ title, status    │ │ title, status    │     │
│  │ domain, profile  │ │ domain, profile  │ │ domain, profile  │     │
│  │ skills           │ │ skills           │ │ skills           │     │
│  │ steps (table)    │ │ steps (table)    │ │ steps (table)    │     │
│  │ verification     │ │ verification     │ │ verification     │     │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## config.toon

Plan-specific configuration created during init phase.

### Location

```
.plan/plans/{plan_id}/config.toon
```

### Format

```toon
# Plan Configuration

domains[1]:
- java

commit_strategy: per_task
create_pr: true
verification_required: true
verification_command: /pm-dev-builder:builder-build-and-fix
branch_strategy: feature
```

### Field Reference

| Field | Type | Required | Values |
|-------|------|----------|--------|
| `domains` | array | Yes | Domain identifiers (java, javascript, etc.) |
| `commit_strategy` | enum | Yes | `per_task`, `per_plan`, `none` |
| `create_pr` | bool | No | true/false (default: true) |
| `verification_required` | bool | No | true/false (default: true) |
| `verification_command` | string | No | Command to run |
| `branch_strategy` | enum | No | `feature`, `direct` |

### Manager

```bash
python3 .plan/execute-script.py pm-workflow:manage-config:manage-config \
  {create|read|get|set|get-domains|get-multi} --plan-id {id}
```

---

## status.toon

Plan lifecycle status with phase tracking.

### Location

```
.plan/plans/{plan_id}/status.toon
```

### Format

```toon
title: Implement JWT Authentication
current_phase: 5-execute

phases[7]{name,status}:
1-init,done
2-refine,done
3-outline,done
4-plan,done
5-execute,in_progress
6-verify,pending
7-finalize,pending

created: 2025-12-02T10:00:00Z
updated: 2025-12-02T14:30:00Z
```

### Phase Table Visualization

```
┌───────────┬─────────────┐
│   Phase   │   Status    │
├───────────┼─────────────┤
│ init      │ done        │ ✓
│ refine    │ done        │ ✓
│ outline   │ done        │ ✓
│ plan      │ done        │ ✓
│ execute   │ in_progress │ ◄── current
│ verify    │ pending     │
│ finalize  │ pending     │
└───────────┴─────────────┘
```

### Status Values

| Status | Meaning |
|--------|---------|
| `pending` | Not started |
| `in_progress` | Currently active |
| `done` | Completed |

### Manager

```bash
python3 .plan/execute-script.py pm-workflow:plan-manage:manage-lifecycle \
  {create|read|set-phase|update-phase|progress|transition} --plan-id {id}
```

---

## request.md

User request document in markdown format.

### Location

```
.plan/plans/{plan_id}/request.md
```

### Format

```markdown
# Request: {title}

## Description

{User's original request text}

## Context

{Additional context, constraints, or requirements}

## Scope

{What is in/out of scope}

## Acceptance Criteria

- {criterion 1}
- {criterion 2}
```

### Manager

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents \
  request {read|write|exists} --plan-id {id}
```

---

## solution_outline.md

Solution design document with deliverables.

### Location

```
.plan/plans/{plan_id}/solution_outline.md
```

### Structure Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    solution_outline.md                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  # Solution: {title}                                         │
│                                                              │
│  plan_id: {plan_id}                                          │
│  created: {timestamp}                                        │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ ## Summary                                    REQUIRED  ││
│  │ 2-3 sentence approach description                       ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ ## Overview                                   REQUIRED  ││
│  │ ASCII diagram showing component relationships           ││
│  │                                                         ││
│  │   ┌──────────┐       ┌──────────┐                       ││
│  │   │ Service  │──────▶│ Handler  │                       ││
│  │   └──────────┘       └──────────┘                       ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ ## Deliverables                               REQUIRED  ││
│  │                                                         ││
│  │   ### 1. {Title}                                        ││
│  │   **Metadata:**                                         ││
│  │   - domain: java                                        ││
│  │   - module: auth-service                                ││
│  │   - change_type: create                                 ││
│  │   - depends: none                                       ││
│  │                                                         ││
│  │   **Profiles:**                                         ││
│  │   - implementation                                      ││
│  │   - testing                                             ││
│  │                                                         ││
│  │   **Affected files:**                                   ││
│  │   - `src/main/java/...`                                 ││
│  │                                                         ││
│  │   **Verification:**                                     ││
│  │   - Command: `mvn test`                                 ││
│  │                                                         ││
│  │   ### 2. {Title}                                        ││
│  │   ...                                                   ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  ## Approach               OPTIONAL                          │
│  ## Dependencies           OPTIONAL                          │
│  ## Risks and Mitigations  OPTIONAL                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Deliverable Fields

| Field | Location | Description |
|-------|----------|-------------|
| `domain` | Metadata | Single domain from config.domains |
| `module` | Metadata | Target module name (from architecture) |
| `change_type` | Metadata | create, modify, refactor, migrate, delete |
| `execution_mode` | Metadata | automated, manual, mixed |
| `depends` | Metadata | Dependencies: none, N. Title, N, M |
| `**Profiles:**` | Block | List of profiles: implementation (always), testing (if applicable) |

### Manager

```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline \
  {write|read|validate|list-deliverables|exists} --plan-id {id}
```

---

## work/ Directory

Working files directory for intermediate data during outline and later phases.

### Location

```
.plan/plans/{plan_id}/work/
```

### Purpose

The `work/` directory stores intermediate files that are:
- Generated during outline phase (inventory scans, analysis results)
- Referenced by other artifacts via `references.toon`
- Plan-specific working data (not archived artifacts)

### Common Files

| File | Phase | Description |
|------|-------|-------------|
| `inventory_raw.toon` | outline | Raw marketplace inventory from scan-marketplace-inventory |
| `inventory_filtered.toon` | outline | Transformed inventory with file paths grouped by type |

### Manager

```bash
# Create work directory
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files mkdir \
  --plan-id {plan_id} --dir work

# Read/write files in work directory
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files read \
  --plan-id {plan_id} --file work/inventory_filtered.toon
```

---

## TASK-NNN-TYPE.toon

Individual task files in the tasks directory.

### Location

```
.plan/plans/{plan_id}/tasks/TASK-{NNN}-{TYPE}.toon
```

### Filename Format

```
TASK-001-IMPL.toon
     │    │
     │    └── Type: IMPL, FIX, SONAR, PR, LINT, SEC, DOC
     │
     └── Sequential number (001, 002, ...)
```

### Format

```toon
number: 1
title: Update misc agents to TOON output
status: pending
phase: 5-execute
domain: plan-marshall-plugin-dev
profile: implementation
origin: plan
created: 2025-12-02T10:30:00Z
updated: 2025-12-02T10:30:00Z

skills:
  - pm-plugin-development:plugin-maintain
  - pm-plugin-development:plugin-architecture

deliverables[3]:
- 1
- 2
- 4

depends_on: TASK-1, TASK-2

description: |
  Migrate miscellaneous agents from JSON to TOON output format.

steps[3]{number,title,status}:
1,pm-plugin-development/agents/tool-coverage-agent.md,pending
2,pm-dev-builder/agents/gradle-builder.md,pending
3,pm-dev-frontend/commands/js-generate-coverage.md,pending

verification:
  commands[1]:
  - grep -L '```json' {files} | wc -l
  criteria: No JSON blocks remain
  manual: false

current_step: 1
```

### Task Structure Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      TASK-001-IMPL.toon                      │
├─────────────────────────────────────────────────────────────┤
│ HEADER                                                       │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ number: 1                                                │ │
│ │ title: Update misc agents...                             │ │
│ │ status: pending → in_progress → done                     │ │
│ │ phase: 5-execute                                         │ │
│ │ domain: plan-marshall-plugin-dev                         │ │
│ │ profile: implementation                                  │ │
│ │ origin: plan | fix                                       │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ CONTEXT                                                      │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ skills:                   Loaded by agent before exec    │ │
│ │   - pm-plugin-dev:plugin-maintain                        │ │
│ │   - pm-plugin-dev:plugin-architecture                    │ │
│ │                                                          │ │
│ │ deliverables[3]: 1, 2, 4  References to solution outline │ │
│ │ depends_on: TASK-1, TASK-2                               │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ STEPS TABLE                                                  │
│ ┌──────┬───────────────────────────────────┬─────────────┐  │
│ │ #    │ Title (file path)                 │ Status      │  │
│ ├──────┼───────────────────────────────────┼─────────────┤  │
│ │ 1    │ pm-plugin-dev/agents/agent1.md    │ done        │  │
│ │ 2    │ pm-dev-builder/agents/builder.md  │ in_progress │  │
│ │ 3    │ pm-dev-frontend/commands/cmd.md   │ pending     │  │
│ └──────┴───────────────────────────────────┴─────────────┘  │
│                                                              │
│ VERIFICATION                                                 │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ verification:                                            │ │
│ │   commands[1]:                                           │ │
│ │     - grep -L '```json' {files} | wc -l                  │ │
│ │   criteria: No JSON blocks remain                        │ │
│ │   manual: false                                          │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Status Flow

```
TASK Status:
  pending ──▶ in_progress ──▶ done
                    │
                    ▼
                 blocked

STEP Status:
  pending ──▶ in_progress ──▶ done
                    │
                    ▼
                 skipped
```

### Task Types

| Type | Suffix | Description |
|------|--------|-------------|
| Implementation | `IMPL` | New feature or enhancement |
| Fix | `FIX` | Bug fix or issue resolution |
| Sonar | `SONAR` | SonarQube issue fix |
| PR Review | `PR` | Pull request feedback |
| Lint | `LINT` | Linting/formatting fix |
| Security | `SEC` | Security issue fix |
| Documentation | `DOC` | Documentation update |

### Manager

```bash
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks \
  {add|update|remove|list|get|next|step-start|step-done|step-skip} --plan-id {id}
```

---

## references.toon (Optional)

External references like GitHub issues.

### Location

```
.plan/plans/{plan_id}/references.toon
```

### Format

```toon
# References

issue:
  number: 123
  url: https://github.com/owner/repo/issues/123
  title: Add JWT validation
  body: |
    Issue description from GitHub

pr:
  number: 456
  url: https://github.com/owner/repo/pull/456
```

### Manager

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references \
  {read|set|append} --plan-id {id}
```

---

## work.log

Semantic work progress tracking across all phases.

### Location

```
.plan/plans/{plan_id}/logs/work.log
```

### Format

```
[{timestamp}] [{level}] [{category}] {message}
  phase: {phase}
  [detail: {additional context}]
```

### Example

```
[2025-12-11T11:14:30Z] [INFO] [PROGRESS] Starting init phase
  phase: 1-init

[2025-12-11T11:15:24Z] [INFO] [ARTIFACT] Created deliverable: auth module
  phase: 3-outline
  detail: Source: request.md, domain: java

[2025-12-11T11:17:55Z] [INFO] [OUTCOME] Task completed: 3 files modified
  phase: 5-execute
```

### Categories

| Category | Purpose |
|----------|---------|
| `PROGRESS` | Phase/step start/end |
| `ARTIFACT` | Files/documents created or modified |
| `OUTCOME` | Results and summaries |
| `FINDING` | Issues or observations |
| `ERROR` | Failures with details |

**Note**: Decision entries go to `decision.log`, not `work.log`.

### Manager

```bash
# Write entry
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} {level} "{message}"

# Read entries
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  read --plan-id {id} --type work [--limit N] [--phase PHASE]
```

---

## decision.log

Dedicated log for decision entries tracking reasoning and choices made during execution.

### Location

```
.plan/plans/{plan_id}/logs/decision.log
```

### Format

Decision entries do NOT include a `[DECISION]` prefix since the file itself indicates the entry type.

```
[{timestamp}] [{level}] {message}
  phase: {phase}
  [detail: {additional context}]
```

### Example

```
[2025-12-11T11:14:48Z] [INFO] (pm-workflow:phase-1-init) Detected domain: java - pom.xml found
  phase: 1-init

[2025-12-11T11:20:15Z] [INFO] (pm-plugin-development:ext-outline-plugin) Scope: bundles=all
  phase: 3-outline
  detail: marketplace/bundles structure detected
```

### Manager

```bash
# Write decision entry
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} {level} "{message}"

# Read decision entries
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  read --plan-id {id} --type decision [--limit N] [--phase PHASE]
```

---

## script-execution.log

Technical script execution tracing (automatic).

### Location

```
.plan/plans/{plan_id}/logs/script-execution.log
```

### Format

```
[{timestamp}] [{level}] [SCRIPT] {notation} {subcommand} ({duration}s)
  [exit_code: {code}]
  [args: {arguments}]
  [stderr: {error output}]
```

### Example

```
[2025-12-11T12:14:26Z] [INFO] [SCRIPT] pm-workflow:manage-files:manage-files create (0.19s)
[2025-12-11T12:15:01Z] [INFO] [SCRIPT] pm-workflow:manage-tasks:manage-tasks add (0.24s)
[2025-12-11T12:17:50Z] [ERROR] [SCRIPT] pm-workflow:manage-config:manage-config set (0.16s)
  exit_code: 2
  args: set --plan-id test --key invalid
  stderr: error: unknown key 'invalid'
```

### Purpose

- Automatic tracing by script executor
- Debugging failed script invocations
- Performance analysis (duration tracking)
- Audit trail for plan execution

### Manager

```bash
# Read entries (read-only, written automatically by executor)
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  read --plan-id {id} --type script [--limit N]
```

**Note**: Entries are written automatically by the script executor. Skills do not write to this log directly.

---

## Artifact Lifecycle

```
PHASE       ARTIFACTS CREATED/UPDATED
─────       ─────────────────────────

init        ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
            │ config.toon │ │ status.toon │ │ request.md  │
            └─────────────┘ └─────────────┘ └─────────────┘
                  │               │               │
                  ▼               ▼               ▼
outline     ┌─────────────────────────────────────────────┐
            │           solution_outline.md                │
            └─────────────────────────────────────────────┘
                                  │
                                  ▼
plan        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
            │ TASK-001-... │ │ TASK-002-... │ │ TASK-003-... │
            └──────────────┘ └──────────────┘ └──────────────┘
                  │               │               │
                  ▼               ▼               ▼
execute     ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
            │ status:done  │ │ status:done  │ │ status:done  │
            │ steps:done   │ │ steps:done   │ │ steps:done   │
            └──────────────┘ └──────────────┘ └──────────────┘
                                  │
                                  ▼
finalize    ┌─────────────────────────────────────────────┐
            │          status.toon: finalize=done          │
            │          (git commit, PR created)            │
            └─────────────────────────────────────────────┘
                                  │
                                  ▼
archive     .plan/archived-plans/{date}-{plan_id}/
            └── All artifacts preserved
```

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [phases.md](phases.md) | 7-phase execution model |
| [data-layer.md](data-layer.md) | manage-* skills that access these files |
| [skill-loading.md](skill-loading.md) | How skills from tasks are loaded |
| `pm-workflow:manage-config` | config.toon operations |
| `pm-workflow:plan-manage:manage-lifecycle` | status.toon operations |
| `pm-workflow:manage-tasks` | TASK-*.toon operations |
| `pm-workflow:manage-solution-outline` | solution_outline.md operations |
| `plan-marshall:manage-logging` | work.log, decision.log, and script-execution.log operations |
