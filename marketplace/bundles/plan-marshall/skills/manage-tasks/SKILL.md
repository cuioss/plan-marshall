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
| `list` | `--plan-id [--status] [--deliverable] [--ready] [--domain] [--profile]` | List all tasks; `--domain` / `--profile` filter the result set |
| `read` | `--plan-id --task-number` | Read single task details |
| `exists` | `--plan-id --task-number` | Boolean presence probe — returns `status: success exists: true\|false`, never errors on absence (use instead of `read` for existence checks) |
| `next` | `--plan-id [--include-context] [--ignore-deps]` | Get next pending task/step |
| `next-tasks` | `--plan-id` | Get all tasks ready for parallel execution |
| `finalize-step` | `--plan-id --task-number --step --outcome [--reason] [--outcome-task-title] [--outcome-step-count] [--outcome-caller]` | Complete step with outcome (done/skipped/failed). When the call closes a task as `done`, the script emits one canonical `[OUTCOME] ({caller}) Completed TASK-NNN: {title} ({M} steps)` work-log line — see "Script-Level [OUTCOME] Emission" below for the contract and overrides. |
| `add-step` | `--plan-id --task-number --target --intent [--after]` | Add step to task |
| `update-step` | `--plan-id --task-number --step-number --intent --reason [--finding-id]` | Update step intent and reason (e.g., to record a triage finding reference) |
| `remove-step` | `--plan-id --task-number --step` | Remove step from task |
| `rename-path` | `--plan-id --old-path --new-path` | Record path rename and rewrite step targets |
| `qgate-mechanical-checks` | `--plan-id [--no-emit]` | Run the six deterministic Q-Gate checks for phase-4-plan Step 9 (coverage, skill-resolution, acyclic, files-exist, keyword-drift, structural-token-drift). Pure regex + graph + filesystem; no LLM dispatch. Each failure becomes a Q-Gate finding under `--source qgate` so phase-4-plan's existing aggregate consumes it. Returns `total_failed`, per-check counts, and an `ambiguous` flag the caller uses to decide whether the LLM q-gate-validation dispatch still needs to fire. |
| `loop-exit-guard` | `--plan-id` | Script-level enforcement of the phase-5-execute "unfinished > 0 → must continue" invariant. The predicate is the union of `pending` AND `in_progress` tasks. Emits `status: continue` (with `pending_count`, `pending_ids`, `in_progress_count`, `in_progress_ids`) when EITHER bucket is non-empty — the non-success status forces the orchestrator to re-dispatch the execution-context. Emits `status: success` (with all four count/id fields present and zero-valued) only when BOTH counts are zero. See "Loop-Exit Guard" below for the contract. |
| `pre-commit-verify-freshness` | `--plan-id` | Script-level enforcement that the worktree state has been observed by a fresh `verify` run before any pre-commit transition. Emits `status: fresh` (verify entry post-dates the worktree mtime), `status: stale` (worktree mutated since the last observed verify), or `status: undecidable` (no positive freshness proof exists — either no matching log entry, or no mtime baseline). Fail-closed contract: only `fresh` permits transition. See "Pre-Commit Verify Freshness" below for the contract. |

### Loop-Exit Guard (`loop-exit-guard`)

`loop-exit-guard` is the script-level enforcement of the phase-5-execute
dispatch loop's "unfinished > 0 → must continue" invariant. The predicate
is the union of two unfinished terminal-state buckets: `pending` (task
never started) AND `in_progress` (task started but not finalized — e.g.,
the dispatch that began it terminated mid-flight). The orchestrator
(`plan-marshall:plan-marshall:execution.md`) consults this verb on every
loop-exit decision before classifying a dispatch as a clean exit; the
phase-5-execute SKILL.md § Step 12a (Pending-tasks transition guard) is a
thin pointer to this verb — the authoritative unfinished-count is here,
not in skill prose.

**Blocking states (resumability):**

| Status | Blocks clean exit? |
|--------|--------------------|
| `pending` | Yes — task never started |
| `in_progress` | Yes — task started but not finalized (mid-flight) |
| `done` | No — terminal success |
| `failed` | No — terminal failure |
| `blocked` | No — explicit triage outcome |

Both `pending` and `in_progress` are unfinished terminal states by the
broadened predicate. Either non-empty bucket forces `status: continue`.

**TOON return contract:**

Both `continue` and `success` branches emit all four count/id fields so
callers can read either axis without conditional presence checks:

```toon
status: continue | success
plan_id: {plan_id}
pending_count: N
pending_ids[N]: [task_numbers]
in_progress_count: M
in_progress_ids[M]: [task_numbers]
message: "..."
```

- `status: continue` with `pending_count > 0` OR `in_progress_count > 0` —
  at least one unfinished task remains. The orchestrator MUST re-dispatch
  the execution-context and MUST NOT classify the return as
  `clean_exit_queue_empty`. The `message` field names which axis was
  non-empty so the orchestrator's log surfaces the reason.
- `status: success` with `pending_count: 0` AND `in_progress_count: 0` —
  queue empty by the broadened predicate, clean exit permitted. The
  boundary-call fence in `plan-marshall/workflow/execution.md` may now
  record `termination-cause == clean_exit_queue_empty`.

**Rationale:** before this verb, the loop-exit decision was driven by the
dispatched agent's terminal payload, which the agent could echo verbatim
(e.g. `task_complete`) without the orchestrator distinguishing "one task
done out of three" from "the queue is empty". Moving the decision to a
script-level read of disk state — the same `get_all_tasks` machinery as
`list --status pending` — closes the control-flow gap. The original
predicate considered only `pending`, which left a residual seam: a task
that flipped to `in_progress` and was abandoned mid-dispatch would leave
the queue "empty by the pending bucket" while the task itself was still
unfinished. Broadening the predicate to `pending OR in_progress` closes
that residual seam.

### Pre-Commit Verify Freshness (`pre-commit-verify-freshness`)

`pre-commit-verify-freshness` is the script-level enforcement of the
necessary-vs-sufficient gap between `loop-exit-guard` (queue-empty proof) and
the pre-commit-push state (worktree-actually-verified proof). `loop-exit-guard`
answers a structurally narrower question ("is the task queue empty?") than
what the pre-commit gate needs ("has the codebase actually been verified
against its current on-disk state?"). This verb closes the gap by comparing
the most recent `plan-marshall:build-pyproject:pyproject_build run` INFO line
in `script-execution.log` against the most recent file-content mtime in the
worktree (scoped to the live plan footprint derived on demand — `{base}...HEAD`
∪ porcelain — falling back to a pruned worktree-root walk when the footprint is
empty; see "Algorithm" below). The
two guards are complementary, not redundant: queue-emptiness and
verify-freshness must BOTH be true before any pre-commit transition.

The gap this closes: the orchestrator can dispatch `commit-push` against a tree
that no full `verify` has observed if the loop-exit guard is the only gate checked.

**Question answered:** is the most recent `verify` log entry newer than the
worktree state it would re-verify?

**Three return statuses (fail-closed contract):**

- `status: fresh` — latest matching INFO build entry post-dates the newest
  worktree mtime. A fresh `verify` has been observed against the current
  on-disk state, so the gate is permitted to pass. Carries `t_build_iso`,
  `t_worktree_iso`, `newest_mtime_path`, and `worktree_root` for the
  audit trail.
- `status: stale` — newest worktree mtime post-dates the most recent build
  entry. The worktree has been mutated since the last observed verify, so
  the gate MUST fail closed. Carries the same audit fields as `fresh`.
- `status: undecidable` — no positive freshness proof exists. Two
  sub-reasons: (a) `reason: no_build_log_entry` — `script-execution.log`
  carries no matching INFO line (or the log file is missing); (b)
  `reason: worktree_mtime_unresolvable` — the worktree root produced no
  candidate files after pruning skip-list directories. Both
  sub-reasons MUST be treated as gate failure.

**Canonical invocation:**

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  pre-commit-verify-freshness --plan-id {plan_id}
```

**Wired-in gates:** the dispatcher prose lives at:

- `phase-5-execute/SKILL.md` § Step 12a — Pending-tasks transition guard
  (now a co-equal gate alongside `loop-exit-guard`).
- `phase-6-finalize/SKILL.md` and `phase-6-finalize/standards/commit-push.md`
  § "Freshness precondition" — fires BEFORE the no-changes-branch check of
  `commit-push`.

Both gates fail closed on any non-`fresh` status and emit a `[BLOCKED]` work-log
line carrying the reason, the newest-mtime path, and both timestamps. The
`--force` orchestrator escape mirrors the existing pending-tasks-guard escape
— deliberate, log-recorded override for triage-driven aborts. Never invoked
programmatically from inside the loop.

**Algorithm (deterministic; no LLM dispatch):**

1. Resolve the plan-scoped `script-execution.log` path via the same
   `.plan/plans/{plan_id}/logs/` resolution used by `manage-logging`.
2. Scan the log for INFO lines matching the literal substring
   `plan-marshall:build-pyproject:pyproject_build run`. Parse the leading
   ISO-8601 timestamp for the newest match as `t_build`.
3. Resolve the worktree root via `status.metadata.worktree_path`; fall back
   to the current working directory when no worktree is materialised.
4. Derive the live plan footprint on demand from the worktree (`{base}...HEAD`
   ∪ porcelain, reading `references.json` only to resolve the base ref). When
   non-empty, compute `t_worktree` as the maximum mtime over the footprint
   entries that still exist on disk (resolved relative to the worktree root).
   When the footprint is empty or all entries are missing, fall back to a
   pruned worktree-root walk that skips `.git/`, `.plan/`, `node_modules/`,
   `__pycache__/`, `.venv/`, `target/`, `build/`, and any other dotted
   directory.
5. Decide: `t_build < t_worktree` → `stale`; otherwise → `fresh`; missing
   either timestamp → `undecidable` with the appropriate `reason`.

The algorithm never raises uncaught exceptions on missing log file, missing
references, or absent worktree — every degenerate input case returns
`undecidable` with a descriptive `reason`.

### Script-Level `[OUTCOME]` Emission (`finalize-step`)

When a `finalize-step --outcome done` call closes the targeted task (i.e. all
steps are `done` AND no step is `failed`), the script emits exactly one
canonical work-log entry **before returning**:

```
[OUTCOME] (plan-marshall:phase-5-execute) Completed TASK-NNN: {task_title} ({M} steps)
```

This emission is **unconditional and lives inside the script boundary** — it
fires for every task completion regardless of which orchestrator dispatched
the closing call. The emission lives inside the script boundary so it fires for every task completion
regardless of which orchestrator dispatched the closing call — a caller-side emission
is lost whenever the caller envelope is re-fired and its working context is discarded
before the `[OUTCOME]` line can be written.

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
  [--deliverable N] [--ready] [--domain DOMAIN] [--profile PROFILE]
```

`--domain` and `--profile` are filter dimensions on `list` — there is no separate
`tasks-by-domain` / `tasks-by-profile` subcommand.

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
  --plan-id PLAN_ID --task-number N --target TEXT --intent INTENT [--after N]
```

### update-step

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks update-step \
  --plan-id PLAN_ID --task-number N --step-number M \
  --intent INTENT --reason TEXT [--finding-id FINDING_ID]
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

### pre-commit-verify-freshness

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks pre-commit-verify-freshness \
  --plan-id PLAN_ID
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

