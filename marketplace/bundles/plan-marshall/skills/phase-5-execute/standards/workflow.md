# Plan Execute Workflow

## Execution Pattern

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      DUMB TASK RUNNER                                    │
│                                                                          │
│      ┌──────────────────────────────────────────────────────────┐       │
│      │                                                          │       │
│      │  1. LOCATE    →  Find current task via manage-tasks      │       │
│      │       │                                                  │       │
│      │       ▼                                                  │       │
│      │  2. EXECUTE   →  Run checklist items (delegate as       │       │
│      │       │           specified in item text)                │       │
│      │       ▼                                                  │       │
│      │  3. UPDATE    →  Mark items [x], call update-progress   │       │
│      │       │                                                  │       │
│      │       ▼                                                  │       │
│      │  4. NEXT      →  Move to next task or phase             │       │
│      │                                                          │       │
│      └──────────────────────────────────────────────────────────┘       │
│                                                                          │
│  NO BUSINESS LOGIC - just sequential execution of checklists.            │
└─────────────────────────────────────────────────────────────────────────┘
```

## Phases Handled

| Phase | Typical Tasks |
|-------|---------------|
| execute | Code implementation, test creation, build verification |
| finalize | Quality checks, commit, PR creation, completion |

## Task Execution

### Reading Tasks

```
Skill: plan-marshall:manage-tasks
operation: next
plan_id: {plan_id}

Returns next task with status pending or in_progress
```

### Executing Checklist Items

For each `- [ ]` item:
1. **Parse** - Understand what action is needed
2. **Delegate** - If item specifies agent/skill/command, invoke it. When a worktree is active, every delegated `Task:` invocation (and any other subagent dispatch that accepts a free-form prompt) MUST include the worktree path in the prompt — the prompt MUST begin with the Worktree Header defined in `standards/operations.md` (see the "Worktree Header Protocol" section at the top of that file for the exact template). Skip the header only when no worktree is active.
3. **Execute** - Perform the action
4. **Update** - Mark item `[x]` via manage-tasks script

### Progress Update

After each step completion:
```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step \
  --plan-id {plan_id} \
  --task-number {task_number} \
  --step {step_number} \
  --outcome done
```

### Artifact Emission at Task Completion

After all steps of a task are complete and verification has passed, but **before** the orchestrator calls `manage-tasks next` to advance to the following task, the orchestrator MUST emit one `[ARTIFACT]` work-log entry per changed path so that a plan-level audit can reconstruct which file system effects each task produced.

**Baseline SHA**: Record the worktree's HEAD SHA the moment a task transitions to `in_progress` and persist it as `task_start_sha` in task metadata. This is the single source of truth for the task's starting point. Capture it with:

```bash
git -C {worktree_path} rev-parse HEAD
```

(Or `git -C . rev-parse HEAD` when no worktree is active — the `cd && git` compound is prohibited; see `dev-general-practices` Hard Rules.)

**Diff computation**: At task completion, compute the name-status diff from the recorded baseline to the current HEAD:

```bash
git -C {worktree_path} diff --name-status {task_start_sha} HEAD
```

Walk each entry of the output and map it to exactly one `[ARTIFACT]` message. Each line of `diff --name-status` output has the shape `{status}\t{path}` (or `{status}\t{old_path}\t{new_path}` for renames/copies):

| Status code | Message shape |
|-------------|---------------|
| `A`, `M` | `[ARTIFACT] (plan-marshall:phase-5-execute:{task_number}) Wrote {relative_path}` |
| `D` | `[ARTIFACT] (plan-marshall:phase-5-execute:{task_number}) Deleted {relative_path}` |
| `R*` (rename, any similarity score) | `[ARTIFACT] (plan-marshall:phase-5-execute:{task_number}) Renamed {old_path} -> {new_path}` |
| `C*` (copy) | Treat as `A` for `{new_path}` — emit a single `Wrote` entry |

Rename entries produce **exactly one** `Renamed` message — never a delete entry for the old path plus a write entry for the new path. This keeps the audit trail unambiguous about the operation's intent.

Emit each entry via the work logger:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[ARTIFACT] (plan-marshall:phase-5-execute:{task_number}) Wrote {relative_path}"
```

Substitute the appropriate message shape per row. Paths are **worktree-relative** (as git emits them). If the diff is empty (no paths changed), emit **nothing** — an empty artifact list is a valid outcome (for example, a pre-implemented task or a verification-profile task that legitimately modified no files). The absence of artifact entries in the work log is itself meaningful signal.

**Caller-format exception**: The `(plan-marshall:phase-5-execute:{task_number})` caller prefix deliberately uses a three-segment form (`bundle:skill:task_number`) rather than the usual two-segment `(bundle:skill)` convention documented in [manage-logging log-format.md](../../manage-logging/standards/log-format.md). The trailing `:{task_number}` segment is an approved extension specific to artifact emission so a log reader can attribute each file change to the exact task that produced it without cross-referencing timestamps against task transitions. The third segment in this exception is always a **numeric task id** — this is distinct from other skills that already carry a third segment of a different kind (e.g., `(plan-marshall:phase-6-finalize:record-metrics)` where the third segment names a sub-topic within the skill). No other skill may emit the three-segment `bundle:skill:{numeric}` form; the numeric-tail shape is reserved for `plan-marshall:phase-5-execute` artifact entries.

## Manifest-Driven Step Selection

The set of Phase 5 verification steps that fire — and whether the entire execute loop runs at all — is **not** chosen at runtime by per-task heuristics or per-standard skip rules. Instead, `phase-4-plan` Step 8b composes a per-plan **execution manifest** (`manage-execution-manifest compose`) that names exactly which built-in verification steps belong to this plan, plus a single `early_terminate` flag for analysis-only plans with no affected files.

`phase-5-execute` is a **dumb manifest executor**:

1. **At phase entry (Step 2)**, read the manifest via `manage-execution-manifest read`.
2. **If `phase_5.early_terminate == true`** — log the decision and transition directly to `phase-6-finalize`, skipping every task and the entire verification loop. This handles analysis-only plans surgically without ever entering the execute loop.
3. **Otherwise** — execute tasks sequentially as documented in `Task Execution` above. The verification step list (`quality-gate`, `module-tests`, `coverage`, etc.) consumed by Step 11b "Final Quality Sweep" comes from `phase_5.verification_steps`.
4. **If `phase_5.verification_steps` is empty** (e.g., docs-only plans where the manifest composer dropped all verification steps) — Step 11b fires no quality sweep at all. The phase still completes normally; absence of a sweep is a valid manifest-driven outcome.
5. **If `phase_5.verification_steps` is non-empty** — Step 11b appends exactly **one** canonical `quality-gate` invocation as the end-of-phase sweep, regardless of whether `quality-gate` already appears in the list. This is the single source of "did the phase end clean?" signal.

**Per-doc skip logic is forbidden in this skill's standards.** The built-in step docs (`quality_check.md`, `build_verify.md`, `coverage_check.md`) carry no embedded skip rules — every "should this step run" decision is encoded in `manage-execution-manifest`'s seven-row decision matrix and flows into the manifest's `verification_steps` list. If a step appears in the manifest, it runs; if it does not, it does not.

The `manage-execution-manifest` skill's [decision-rules.md](../../manage-execution-manifest/standards/decision-rules.md) is the authoritative table for which step combinations fire under which inputs.

## Phase Transition

When all tasks in phase complete:

1. **Automatic file collection** (execute phase):
   - `manage-status transition` collects modified files
   - Updates `references.json` with changed files
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-status:manage_status transition --plan-id {plan_id} --completed {phase}
   ```

2. **Auto-transition** to next phase:
   - execute → finalize
   - finalize → complete

3. **No user prompt** for transitions (continuous execution)

## Auto-Continue Rules

**Continue without prompting**:
- Task completion
- Phase transition
- Routine operations

**Stop and prompt when**:
- Error blocks progress
- Multiple valid approaches exist
- User explicitly requested confirmation

## Pre-Implemented Work

Before executing, check if deliverables already exist:
1. Verify files/components exist
2. Check acceptance criteria met
3. If pre-implemented: Still mark progress, then skip to next task
