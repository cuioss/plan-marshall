---
name: manage-tasks
description: Manage implementation tasks with sequential sub-steps within a plan
user-invocable: false
scope: plan
---

# Manage Tasks Skill

Manage implementation tasks with sequential sub-steps within a plan. Each task references deliverables from the solution document and contains ordered steps for execution.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Do not bypass dependency checking unless explicitly using `--ignore-deps`
- Task numbering is sequential and immutable (TASK-001, TASK-002, etc.)
- Adding a task uses the three-step path-allocate pattern: `prepare-add` → write TOON file → `commit-add`. No multi-line content is marshalled through the shell boundary.
- Step finalization requires explicit `--outcome` (done, skipped, or failed)

## Storage Location

Tasks are stored in the plan directory:

```
{plan_dir}/tasks/
  TASK-001.json
  TASK-002.json
  TASK-003.json
```

**Filename format**: `TASK-{NNN}.json` (task type is stored in the JSON `type` field)

---

## File Format (Summary)

Tasks are stored as `TASK-{NNN}.json`. Key fields for quick reference:

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Task title |
| `status` | enum | `pending`, `in_progress`, `done`, `blocked` |
| `domain` | string | Task domain (e.g., java, javascript) |
| `profile` | string | Workflow profile (`implementation`, `module_testing`, `integration_testing`, `quality`, `verification`) |
| `skills` | list | Pre-resolved domain skills (`{bundle}:{skill}` format) |
| `origin` | string | Task origin: `plan`, `fix`, `sonar`, `pr`, `lint`, `security`, `documentation` |
| `deliverable` | int | Referenced deliverable number (1:1 constraint) |
| `steps` | array | Ordered file-path targets with status |

See [standards/task-contract.md](standards/task-contract.md) for the complete field specification, status model, dependency format, skills inheritance, and optimization workflow.

---

## Operations

Script: `plan-marshall:manage-tasks:manage-tasks`

| Command | Parameters | Description |
|---------|------------|-------------|
| `prepare-add` | `--plan-id [--slot]` | Allocate a scratch path under `<plan>/work/pending-tasks/` (Step 1 of add flow) |
| `commit-add` | `--plan-id [--slot]` | Read the prepared TOON file, validate, create TASK-NNN.json, delete scratch (Step 3 of add flow) |
| `batch-add` | `--plan-id (--tasks-file PATH \| --tasks-json JSON \| stdin)` | Atomically create N tasks from a JSON array. Preferred form is `--tasks-file PATH` pointing at a staged plan-relative file (e.g. `work/tasks-batch.json`); `--tasks-json` and stdin remain available for trivial payloads. The two flags are mutually exclusive. All-or-nothing semantics: if any entry fails validation, no `TASK-NNN.json` is written. |
| `update` | `--plan-id --task-number [--title] [--description] [--depends-on] [--status] [--domain] [--profile] [--skills] [--deliverable]` | Update task metadata |
| `remove` | `--plan-id --task-number` | Remove a task |
| `list` | `--plan-id [--status] [--deliverable] [--ready]` | List all tasks |
| `read` | `--plan-id --task-number` | Read single task details |
| `exists` | `--plan-id --task-number` | Boolean presence probe — returns `status: success exists: true\|false`, never errors on absence (use instead of `read` for existence checks) |
| `next` | `--plan-id [--include-context] [--ignore-deps]` | Get next pending task/step |
| `tasks-by-domain` | `--plan-id --domain` | List tasks filtered by domain |
| `tasks-by-profile` | `--plan-id --profile` | List tasks filtered by profile |
| `next-tasks` | `--plan-id` | Get all tasks ready for parallel execution |
| `finalize-step` | `--plan-id --task-number --step --outcome [--reason] [--outcome-task-title] [--outcome-step-count] [--outcome-caller]` | Complete step with outcome (done/skipped/failed). When the call closes a task as `done`, the script emits one canonical `[OUTCOME] ({caller}) Completed TASK-NNN: {title} ({M} steps)` work-log line — see "Script-Level [OUTCOME] Emission" below for the contract and overrides. |
| `add-step` | `--plan-id --task-number --target [--after]` | Add step to task |
| `remove-step` | `--plan-id --task-number --step` | Remove step from task |
| `rename-path` | `--plan-id --old-path --new-path` | Record path rename and rewrite step targets |
| `qgate-mechanical-checks` | `--plan-id [--no-emit]` | Run the six deterministic Q-Gate checks for phase-4-plan Step 9 (coverage, skill-resolution, acyclic, files-exist, keyword-drift, structural-token-drift). Pure regex + graph + filesystem; no LLM dispatch. Each failure becomes a Q-Gate finding under `--source qgate` so phase-4-plan's existing aggregate consumes it. Returns `total_failed`, per-check counts, and an `ambiguous` flag the caller uses to decide whether the LLM q-gate-validation dispatch still needs to fire. |

### Script-Level `[OUTCOME]` Emission (`finalize-step`)

When a `finalize-step --outcome done` call closes the targeted task (i.e. all
steps are `done` AND no step is `failed`), the script emits exactly one
canonical work-log entry **before returning**:

```
[OUTCOME] (plan-marshall:phase-5-execute) Completed TASK-NNN: {task_title} ({M} steps)
```

This emission is **unconditional and lives inside the script boundary** — it
fires for every task completion regardless of which orchestrator dispatched
the closing call. The motivating gap (lesson `2026-05-08-14-001`) was that the
caller-side emission in `phase-5-execute` was lost whenever a per-task
`phase-5-execute` dispatch was re-fired and the original envelope's working context
was discarded before its `[OUTCOME]` line could be written. Moving the emission into the script
removes the dependency on the caller's working context.

**Defaults** (used when the optional overrides below are omitted):

| Field | Default |
|-------|---------|
| `caller` | `plan-marshall:phase-5-execute` |
| `task_title` | The `title` field of the task on disk |
| `step_count` | `len(task.steps)` |

**Optional overrides** (rarely needed; mainly for tests and non-default callers):

| Flag | Effect |
|------|--------|
| `--outcome-task-title TEXT` | Override `{task_title}` in the rendered line. |
| `--outcome-step-count N` | Override `{M}` (the step count) in the rendered line. |
| `--outcome-caller BUNDLE:SKILL` | Override the `({caller})` marker in the rendered line. |

The emission only fires for the *task-closing* call (the final step that
flips the task to `done`). It does NOT fire for `--outcome skipped`,
`--outcome failed`, or for intermediate `--outcome done` calls that leave the
task `in_progress`. Caller-side `[OUTCOME]` emissions in skills MUST NOT
duplicate this line — the script-level guard is the single source of truth.

### Add Flow — Three-Step Path-Allocate Pattern

Adding a task uses the same path-allocate pattern as every other content-passing
surface in the bundle. The script allocates a scratch path; the main context
writes the TOON definition directly with its native Write/Edit tools; a second
subcommand reads the file, validates it, creates `TASK-NNN.json`, and deletes
the scratch. No multi-line content ever crosses the shell boundary.

```bash
# Step 1: script allocates a scratch path under <plan>/work/pending-tasks/
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  prepare-add --plan-id {plan_id}
# → returns {path: /abs/.../work/pending-tasks/default.toon}

# Step 2: main context writes the TOON task definition to that path with Write/Edit.
# (No shell marshalling, no escaped \n. The Write tool does the work.)

# Step 3: script reads the file, validates it, and creates the task
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  commit-add --plan-id {plan_id}
# → returns {status: success, file: TASK-003.json, ...}
```

**Concurrent adds**: pass `--slot <name>` to `prepare-add` and `commit-add` to
run multiple pending tasks side-by-side. Slot names must match
`[a-z0-9][a-z0-9-]{0,63}`. Omitting `--slot` uses the reserved slot `default`.

**TOON file format** (written to the path returned by `prepare-add`):

```toon
title: My Task Title
deliverable: 1
domain: plan-marshall-plugin-dev
profile: implementation
origin: plan
description: |
  Multi-line task description here.
  Can include any characters.

skills:
  - pm-plugin-development:plugin-maintain
  - pm-plugin-development:plugin-architecture

steps:
  - First step to execute
  - Second step to execute
  - Third step to execute

depends_on: none

verification:
  commands:
    - grep -l '```json' marketplace/bundles/*.md | wc -l
    - mvn verify
  criteria: All grep commands return 0 (no JSON blocks remain)
  manual: false
```

**Required fields**: `title`, `deliverable`, `domain`, `profile`, `skills`, `steps`

**Optional fields**: `description`, `depends_on`, `verification`, `origin` (default: plan)

**Field values**:
- `deliverable`: Single positive integer (one deliverable per task, 1:1 constraint)
- `domain`: Domain from references.json (e.g., `java`, `javascript`, `plan-marshall-plugin-dev`)
- `profile`: Profile key from marshal.json. Standard profiles: `implementation`, `module_testing`, `integration_testing`, `quality`, `verification`, `standalone`
- `skills`: Array of `bundle:skill` format strings
- `depends_on`: `none` or task references like `TASK-1, TASK-2`
- `origin`: `plan` (from task-plan), `fix` (from verify), `sonar`, `pr`, `lint`, `security`, or `documentation`

### List/Next Filters

| Parameter | Description |
|-----------|-------------|
| `--deliverable` | Filter by deliverable number |
| `--ready` | Only tasks with satisfied dependencies |
| `--ignore-deps` | (next only) Ignore dependency constraints |

---

## Quick Examples

### Add a task

```bash
# Step 1: allocate scratch path
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  prepare-add --plan-id my-feature

# Step 2: Write tool writes TOON content to the returned path, e.g.:
#   title: Update misc agents to TOON
#   deliverable: 1
#   domain: java
#   description: Migrate miscellaneous agents from JSON to TOON output format.
#   steps:
#     - file1.md
#     - file2.md
#     - file3.md
#   verification:
#     commands:
#       - mvn verify
#     criteria: Build passes

# Step 3: commit
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  commit-add --plan-id my-feature
```

### Add a task with dependencies

Same three-step flow. The TOON definition written in Step 2 simply adds:

```toon
depends_on: TASK-1, TASK-2
```

### Concurrent adds with slots

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  prepare-add --plan-id my-feature --slot impl

python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  prepare-add --plan-id my-feature --slot tests

# ... Write TOON to both returned paths ...

python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  commit-add --plan-id my-feature --slot impl

python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  commit-add --plan-id my-feature --slot tests
```

### Atomic batch add (many tasks in one call)

`batch-add` accepts a JSON array of task records and atomically appends every
task in a single invocation. It is the recommended path when the caller already
has a structured task plan (e.g. `phase-4-plan` creating multiple tasks per
deliverable) and would otherwise run N×(`prepare-add` + Write + `commit-add`).

Semantics:

- **All-or-nothing**: every entry is validated before any file is written. On
  any validation failure the whole batch is rejected and no `TASK-NNN.json`
  file is created.
- **Sequential numbering**: numbers are assigned starting at the next
  available slot at call time and increment in array order.
- **Empty array** (`"[]"`) is a documented no-op that returns
  `tasks_created: 0`.
- The JSON array shape is documented in
  `standards/task-contract.md` § "Atomic Batch Insertion (`batch-add`)".

**Canonical form — `--tasks-file PATH` (path-allocate flow)**: stage the JSON
array under the plan's `work/` tree via `manage-files write`, then point
`batch-add` at the staged file. This keeps large batches off the shell
argument boundary, makes the input auditable as a plan artifact, and is the
form used by `phase-4-plan`:

```bash
# Step 1: stage the JSON array as a plan-relative file under work/
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files \
  write --plan-id my-feature --file work/tasks-batch.json \
  --content '[{"title":"Task A","deliverable":1,"domain":"java","profile":"implementation","skills":[],"steps":["src/main/java/A.java"]},{"title":"Task B","deliverable":1,"domain":"java","profile":"module_testing","skills":[],"steps":["src/test/java/ATest.java"],"depends_on":["TASK-1"]}]'

# Step 2: persist the batch atomically by pointing batch-add at the staged file
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks batch-add \
  --plan-id my-feature \
  --tasks-file .plan/local/plans/my-feature/work/tasks-batch.json
```

**Secondary form — inline `--tasks-json` (trivial payloads only)**: provide
the array directly on the command line. This form is mutually exclusive with
`--tasks-file` and is intended for small, hand-written payloads where the
shell escaping cost is negligible. Phase-4-plan does NOT use this form.

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks batch-add \
  --plan-id my-feature \
  --tasks-json '[{"title":"Task A","deliverable":1,"domain":"java","profile":"implementation","skills":[],"steps":["src/main/java/A.java"]}]'
```

The batch path replaces the per-task `prepare-add` + Write + `commit-add`
sequence in callers that produce many tasks at once. Single ad-hoc adds may
keep using the path-allocate flow.

### Probe whether a task exists (boolean — never errors on absence)

Use `exists` instead of `read` whenever the call is a presence check rather
than a data fetch. `read` returns exit code 1 (with an error TOON record)
when the task is absent — every such call shows up as a `[ERROR]` row in
`script-execution.log`, even when the caller intended to handle absence.
`exists` returns `status: success exists: true|false` for any task number,
so absence stays silent.

```bash
# Probe — always returns status: success
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks exists \
  --plan-id my-feature \
  --task-number 7
# → status: success
#   plan_id: my-feature
#   task: 7
#   exists: true|false
```

Pair `exists` with `read` when the caller needs the task body only after
confirming presence — the two-call pattern keeps the failure logs clean
without changing observable behavior.

### Get next task/step (respects dependencies)

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks next \
  --plan-id my-feature
```

### List ready tasks only

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks list \
  --plan-id my-feature \
  --ready
```

### Finalize step (mark done, skipped, or failed)

```bash
# Mark step as done
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step \
  --plan-id my-feature \
  --task-number 2 \
  --step 3 \
  --outcome done

# Skip step with reason
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step \
  --plan-id my-feature \
  --task-number 2 \
  --step 3 \
  --outcome skipped \
  --reason "File already exists"

# Mark step as failed with reason
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step \
  --plan-id my-feature \
  --task-number 2 \
  --step 3 \
  --outcome failed \
  --reason "Verification failed: test suite has 3 failures"
```

---

## Integration

### Producers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-4-plan` | `prepare-add`, `commit-add` | Create tasks from deliverables |
| `phase-5-execute` | `update`, `finalize-step` | Update task/step status during execution |
| Q-Gate iteration | `prepare-add`, `commit-add` | Create fix tasks from verification findings |

### Consumers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-5-execute` | `next`, `next-tasks`, `read` | Retrieve tasks for execution |
| `phase-6-finalize` | `list` | Query task completion for PR summary |
| Task executors | `read`, `finalize-step` | Read task details and mark steps done |

### With phase-4-plan dispatch

The `phase-4-plan` task-planning dispatch creates tasks during plan refinement using the three-step flow:

```bash
# Step 1
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  prepare-add --plan-id {plan_id}

# Step 2: Write TOON definition to the returned path via the Write tool
#   title: {task_title}
#   deliverable: {deliverable_number}
#   domain: {domain}
#   steps:
#     - {step1}
#     - {step2}
#   depends_on: none

# Step 3
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  commit-add --plan-id {plan_id}
```

### With plan-execute

Plan-execute iterates through tasks:
```
LOOP:
  1. manage-tasks next --plan-id {plan_id}
  2. IF no next: DONE
  3. SPAWN implement agent
  4. CONTINUE
```

### With implement-agent

Implement agents execute steps:
```
1. manage-tasks read --plan-id {plan_id} --task-number {N}
2. FOR EACH step: execute → finalize-step --outcome done|failed
3. RUN verification
```

---

## Deliverable-to-Task Relationship

Tasks reference deliverables from `solution_outline.md` using the `deliverable` field in stdin.

**Constraint**: Each task maps to exactly **one** deliverable (the `deliverable` field is a single integer, not a list). However, one deliverable can produce multiple tasks.

| Pattern | Description | Example |
|---------|-------------|---------|
| Simple | One task per deliverable | TASK-1 has `deliverable: 1`, TASK-2 has `deliverable: 2` |
| Multi-profile | One deliverable, multiple tasks | TASK-1 (implementation) and TASK-2 (module_testing) both have `deliverable: 1` |

**Multi-profile pattern**: When a deliverable needs both implementation and testing, phase-4-plan creates separate tasks per profile. Each task gets its own skill set and executor.

---

## Dependency Management

Tasks can depend on other tasks using the `depends_on` field in stdin:

```yaml
# Task 3 waits for Task 1 and Task 2 to complete
depends_on: TASK-1, TASK-2

# No dependencies
depends_on: none
```

**Dependency enforcement**:
- `next` command only returns tasks with satisfied dependencies
- Use `--ignore-deps` to bypass dependency checking
- Use `--ready` filter to list only ready tasks

**Blocked output**: When tasks are blocked by dependencies, `next` returns:

```toon
next: null
blocked_tasks[2]{number,title,waiting_for}:
1,Write tests,TASK-3
2,Deploy,TASK-3, TASK-4
```

---

## Status Model

**Task Status**: `pending` → `in_progress` → `done` | `failed` (or `blocked`)

**Step Status**: `pending` → `in_progress` → `done` | `skipped` | `failed`

---

## Verification

The `verification` field is optional. When present:
- `commands`: List of shell commands to run after implementation (copied verbatim from deliverable's Verification field by phase-4-plan)
- `criteria`: Human-readable success criteria
- `manual`: If `true`, verification requires human judgment (automated commands may still run but results need review)

If a deliverable has no Verification section, the task is created without `verification`.

---

## Canonical invocations

The canonical argparse surface for `manage-tasks.py`. The D4 plugin-doctor analyzer
(`_analyze_manage_invocation.py`) reads this section as source-of-truth for markdown
notation occurrences across the marketplace. Consuming skills xref this section by
name (e.g., "see `manage-tasks` Canonical invocations → `finalize-step`") instead
of restating the command inline.

### prepare-add

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks prepare-add \
  --plan-id PLAN_ID [--slot SLOT]
```

### commit-add

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks commit-add \
  --plan-id PLAN_ID [--slot SLOT]
```

### batch-add

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks batch-add \
  --plan-id PLAN_ID \
  [--tasks-json JSON | --tasks-file PATH]
```

`--tasks-json` and `--tasks-file` are mutually exclusive. When neither flag is
supplied the array is read from stdin.

### update

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks update \
  --plan-id PLAN_ID --task-number N \
  [--title TEXT] [--description TEXT] [--depends-on REFS ...] \
  [--status {pending|in_progress|done|blocked}] \
  [--domain DOMAIN] [--profile PROFILE] [--skills CSV] [--deliverable N]
```

### remove

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks remove \
  --plan-id PLAN_ID --task-number N
```

### list

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks list \
  --plan-id PLAN_ID \
  [--status {pending|in_progress|done|blocked|all}] \
  [--deliverable N] [--ready]
```

### read

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks read \
  --plan-id PLAN_ID --task-number N
```

### exists

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks exists \
  --plan-id PLAN_ID --task-number N
```

### next

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks next \
  --plan-id PLAN_ID \
  [--include-context] [--ignore-deps]
```

### tasks-by-domain

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks tasks-by-domain \
  --plan-id PLAN_ID --domain DOMAIN
```

### tasks-by-profile

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks tasks-by-profile \
  --plan-id PLAN_ID --profile PROFILE
```

### next-tasks

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks next-tasks \
  --plan-id PLAN_ID
```

### finalize-step

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step \
  --plan-id PLAN_ID --task-number N --step N \
  --outcome {done|skipped|failed} \
  [--reason TEXT] \
  [--outcome-task-title TEXT] [--outcome-step-count N] [--outcome-caller TEXT]
```

### add-step

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks add-step \
  --plan-id PLAN_ID --task-number N --target TEXT [--after N]
```

### remove-step

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks remove-step \
  --plan-id PLAN_ID --task-number N --step N
```

### rename-path

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks rename-path \
  --plan-id PLAN_ID --old-path PATH --new-path PATH
```

### qgate-mechanical-checks

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks qgate-mechanical-checks \
  --plan-id PLAN_ID [--no-emit]
```

---

## Error Responses

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error Code | Cause |
|------------|-------|
| `invalid_plan_id` | plan_id format invalid |
| `task_not_found` | Task number doesn't exist |
| `step_not_found` | Step number doesn't exist in task |
| `invalid_content` | TOON content parsing failed or missing required fields |
| `missing_required` | Required field missing (title, deliverable, domain, profile, skills, steps) |
| `circular_dependency` | Task dependency creates a cycle (detected during `next`) |
| `invalid_outcome` | Step outcome not `done`, `skipped`, or `failed` |
| `plan_dir_not_found` | Plan directory doesn't exist |

---

## Related

- `manage-solution-outline` — Source of deliverables that tasks reference
- `manage-status` — Plan lifecycle tracking; phase transitions gate task execution
- `manage-config` — Skill domain resolution for task profiles
- `manage-findings` — Q-Gate findings may trigger fix tasks during execution

