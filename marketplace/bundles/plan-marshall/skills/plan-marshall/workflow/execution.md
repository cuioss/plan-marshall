# Execution Workflows (Phases 5 & 7)

Workflows for plan execution phases: execute (task implementation + verification) and finalize (commit, PR).

> **cwd for `.plan/execute-script.py` calls**: `manage-*` scripts (Bucket A) resolve `.plan/` via `git rev-parse --git-common-dir` and work from any cwd — do **NOT** pin cwd, do **NOT** pass routing flags, and never use `env -C`. Build / CI / Sonar scripts (Bucket B) accept `--plan-id {plan_id}` (preferred — auto-resolves the worktree via `manage-status get-worktree-path`) or `--project-dir {worktree_path}` (escape hatch / explicit override); the two flags are mutually exclusive. See `plan-marshall:tools-script-executor/standards/cwd-policy.md`.

## Phase Handshake

Every phase transition is guarded by the `phase_handshake` script, which captures a fingerprint of key invariants on phase completion and verifies them on the next phase's entry. Drift between captured and observed invariants blocks progress until resolved or overridden. See [`../references/phase-handshake.md`](../references/phase-handshake.md) for the full contract, storage format, and invariant registry. The entry/completion protocols in [`phase-lifecycle.md`](../../ref-workflow-architecture/standards/phase-lifecycle.md) invoke the handshake automatically for all 6 phases.

## Action Routing

| Action | Workflow |
|--------|----------|
| `execute` (default) | Run execute phase (task iteration + verification) |
| `finalize` | Run finalize phase (commit, PR) |

### Default (no parameters)

Shows executable plans for selection:

```
Executable Plans:

1. jwt-authentication [execute] - Task 3/12: "Add token validation"
2. user-profile-api [finalize] - Ready to commit

0. Exit (use /plan-marshall to create or refine plans)

Select plan to execute:
```

### With plan parameter

Execute specific plan from its current phase:

If plan is in 1-init, 3-outline, or 4-plan phase:
```
Plan 'jwt-auth' is in '3-outline' phase.

This workflow handles 5-execute/6-finalize phases only.
Use /plan-marshall to complete 1-init through 4-plan phases first.
```

---

## Execute Phase (DUMB LOOP Pattern)

**Metrics**: The start of `5-execute` was already recorded by the
`4-plan → 5-execute` fused boundary call emitted at the end of the planning
workflow (see `workflow/planning.md`). When the execute workflow is entered
directly (e.g. via `/plan-marshall action=execute plan={plan_id}` against a
plan already past `4-plan`), use a fused boundary call to close the
previously active phase and start `5-execute` in one step:

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics phase-boundary \
  --plan-id {plan_id} --prev-phase 4-plan --next-phase 5-execute
```

**Phase handshake** (direct-entry variant): capture the just-closed `4-plan` phase before continuing. When entering after the planning workflow already captured `4-plan`, this is idempotent — `capture` upserts the row.

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake capture \
  --plan-id {plan_id} --phase 4-plan
```

**Phase handshake (verify)**: Before iterating tasks, verify the captured invariants for `4-plan` still match the live state. Stop on `status: drift`.

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake verify \
  --plan-id {plan_id} --phase 4-plan --strict
```

The execute phase iterates through tasks using a simple loop:

```bash
# Get next pending task
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks next --plan-id {plan_id}

# After each step completion, finalize step
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step --plan-id {plan_id} --task-number {task_number} --step {step_number} --outcome done
```

For each task:
1. Read task details via manage-tasks
2. Delegate to domain agent based on domain
3. Mark task complete
4. Repeat until all tasks done

### After phase-agent returns

After every `phase-agent` dispatch returns control to the orchestrator —
whether the agent ran the full execute loop to completion, voluntarily
emitted a "Returning control" line with pending tasks, was cancelled by the
host platform, raised a fatal error, or returned for a reason the
orchestrator cannot classify — the orchestrator MUST record the termination
boundary by calling `manage-metrics record-dispatch-boundary` with parsed
`<usage>` totals and a classified termination cause. The accumulating
artifact at `work/metrics-dispatch-boundaries-5-execute.toon` is the
audit trail that `plan-retrospective` correlates with `[OUTCOME]`-log
coverage gaps to detect agent-initiated re-dispatch (lesson
`2026-05-08-14-001`).

**Termination-cause classification** — the orchestrator MUST classify every
return into exactly one of the five values below. The detection rules apply
to the agent's terminal payload (text + structured TOON return):

| Cause | Detection rule |
|-------|----------------|
| `task_complete_returned_verbatim` | The agent returned the bare `task_complete` payload from `execute-task` verbatim, without wrapping it in a phase-5-execute terminal payload. (Implies the agent skipped the loop's bookkeeping after a single task.) |
| `voluntary_checkpoint` | The agent emitted any of "Returning control to orchestrator", "progress checkpoint", "partial-completion handoff", or returned a non-error payload while pending tasks remain in the queue. |
| `harness_cancellation` | The dispatch ended with a host-platform cancellation marker (timeout, context-window limit, etc.). |
| `error` | The agent returned a structured error payload via the skill's Error Handling section (including the pending-task-drift fatal error). |
| `unknown` | Fallback when the orchestrator cannot match any of the above; also the canonical value for clean exits where the loop drove to completion AND the queue is empty. |

**Bash invocation** — issue the call **before** any subsequent dispatch or
phase-boundary action so the audit trail captures the actual termination
order:

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics record-dispatch-boundary \
  --plan-id {plan_id} --phase 5-execute --termination-cause {cause} \
  --total-tokens {n} --tool-uses {n} --duration-ms {n}
```

Substitute `{cause}` with one of the five values from the table above and
`{n}` with the integer parsed from the agent's `<usage>...</usage>` block
(use `0` when the field is absent).

**Boundary-call fence** — the existing `5-execute → 6-finalize` fused
`phase-boundary` call MUST only fire on a clean exit, defined as
`termination-cause == unknown` AND `manage-tasks list --status pending`
returning zero pending tasks. For every other classified cause, the
orchestrator MUST re-dispatch the phase-agent (recoverable cases) or escalate
to the user (`error` / repeated `harness_cancellation`) — it MUST NOT
transition to `6-finalize` while pending work remains. This fence is the
control-flow analogue of the Step 12a "Pending-tasks transition guard" in
`phase-5-execute` SKILL.md and is the structural complement to the
script-level `[OUTCOME]` guard introduced in `manage-tasks finalize-step`.

### Execute Phase Completion

After all tasks complete, transition and check auto-continue:

**Metrics**: During the task loop, maintain a running sum of `total_tokens`,
`tool_uses`, and `duration_ms` from each task agent's `<usage>` tag. After
all tasks complete, record the `5-execute → 6-finalize` boundary in a single
fused call (forwarding the aggregated totals to the closing phase):
```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics phase-boundary \
  --plan-id {plan_id} --prev-phase 5-execute --next-phase 6-finalize \
  --total-tokens {sum of total_tokens from all task agent <usage> tags} \
  --tool-uses {sum of tool_uses from all task agent <usage> tags} \
  --duration-ms {sum of duration_ms from all task agent <usage> tags}
```

**Phase handshake**: Capture invariants for the just-completed `5-execute` phase. Verification of this row happens at the `6-finalize` entry below.

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake capture \
  --plan-id {plan_id} --phase 5-execute
```

The fused call already recorded the start of `6-finalize`; the
**Finalize Phase** section below MUST NOT call `start-phase 6-finalize`
again.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status transition \
  --plan-id {plan_id} --completed 5-execute
```

**Config check** — Read `finalize_without_asking` to determine next action:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get --field finalize_without_asking --audit-plan-id {plan_id}
```

**IF `finalize_without_asking == true`**:
- Log: `"(plan-marshall:plan-marshall) Config: finalize_without_asking=true — auto-continuing to finalize"`
- Continue to **Finalize Phase** below

**ELSE (default)**:
- Display: `"Execute phase complete. Ready to finalize."`
- Display: `"Run '/plan-marshall action=finalize plan={plan_id}' when ready."`
- **STOP**

---

## Finalize Phase

**Metrics**: The start of `6-finalize` was already recorded by the
`5-execute → 6-finalize` fused boundary call above (or by an equivalent
boundary when the finalize workflow is entered directly). Skip any explicit
`start-phase 6-finalize` invocation here. When entering this section
directly without a preceding execute phase in the same orchestration cycle,
use a fused boundary call to close the previously active phase and start
`6-finalize`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics phase-boundary \
  --plan-id {plan_id} --prev-phase {prev_phase} --next-phase 6-finalize
```

**Phase handshake** (direct-entry variant): capture the just-closed `{prev_phase}` phase. When entering after the execute workflow already captured `5-execute`, this is idempotent — `capture` upserts the row.

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake capture \
  --plan-id {plan_id} --phase {prev_phase}
```

**Phase handshake (verify)**: Before dispatching `phase-6-finalize`, verify the captured invariants for the previous phase still match the live state. Stop on `status: drift`. Use `5-execute` when entering after the execute workflow, otherwise the same `{prev_phase}` value used in the fused boundary call above.

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake verify \
  --plan-id {plan_id} --phase {prev_phase} --strict
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:plan-marshall) Loading plan-marshall:phase-6-finalize"
```

Resolve the current Claude Code `session_id` from the hook-populated cache before dispatching the skill. Pass it alongside `plan_id` so `default:record-metrics` can call `manage-metrics enrich` on the live plan directory before `default:archive-plan` moves it.

**Resolve `session_id`:**

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:manage_session current
```

Parse `session_id` from the TOON output. On `status: error\nerror: session_id_unavailable`, abort the finalize phase with a clear message — do **not** invent a filler value and do **not** reach for any `$VAR` expansion. See `phase-6-finalize/SKILL.md` → "How to obtain session_id" for the full resolver contract and forbidden patterns.

**Dispatch the skill:**

```
Skill: plan-marshall:phase-6-finalize
operation: finalize
plan_id: {plan_id}
session_id: {resolved session_id from resolver above}
```

> **Placeholder contract**: every `{}` in a `Skill:` dispatch template in this workflow must have a documented resolver adjacent to it. `{plan_id}` is the top-level workflow parameter; `{session_id}` is resolved by the script above. Do not add new `{}` placeholders without naming the resolver alongside.

Handles:
- Commit and push changes
- Create PR (if configured)
- Automated review (CI, bot feedback)
- Sonar roundtrip (if configured)
- Knowledge capture (advisory)
- Lessons capture (advisory)
- Record final metrics (`end-phase` + `enrich` + `generate`, inside `default:record-metrics` — plan finalization has no "next phase" so the fused `phase-boundary` does not apply here)
- Mark plan complete
- Archive plan (move to `.plan/archived-plans/`)

All three `manage-metrics` commands (`end-phase`, `enrich`, `generate`) are executed inside `default:record-metrics` on the live plan directory before `default:archive-plan` runs. The fused `phase-boundary` subcommand is intentionally NOT used here because plan finalization has no "next phase" to start. Do NOT add any `manage-metrics` invocation after `Skill: plan-marshall:phase-6-finalize` returns — a post-archive write recreates `.plan/local/plans/{plan_id}/` as an orphan directory.

### Loop-back continuation

When `phase-6-finalize` returns with a loop-back signal (`status: loop_back`, `next_phase: 5-execute`) — caused by a step recording `outcome: loop_back` (FIX disposition on a `pr-comment` finding, `pr-comment-overflow` capture, or sonar-roundtrip FIX) — the orchestrator's behaviour mirrors the forward `finalize_without_asking` shape but is gated by the symmetric reverse-direction knob.

**Config check** — Read `loop_back_without_asking` to determine the next action:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize get --field loop_back_without_asking --audit-plan-id {plan_id}
```

**IF `loop_back_without_asking == true`**:
- Log: `"(plan-marshall:plan-marshall) Config: loop_back_without_asking=true — auto-continuing to execute pipeline"`
- The actual inline dispatch is performed inside `phase-6-finalize/SKILL.md` Step 3 § Loop-back continuation hook (item 7b in the Step 3 dispatch loop). The hook re-dispatches `Skill: plan-marshall:phase-5-execute --plan-id {plan_id}` against the freshly-allocated fix tasks, then re-enters the finalize FOR loop with the resumable re-entry check skipping already-`done` steps. The hook is capped by `phase-6-finalize.max_iterations` (default 3); beyond that the loop halts and prompts the user even with this flag set.
- The hook then transitions `5-execute → 6-finalize` via the standard `phase-5-execute.finalize_without_asking` gate. When that gate is `false`, the inline cycle halts at the same prompt the forward path uses — so symmetric loop-back is doubly-gated: both `loop_back_without_asking` AND `finalize_without_asking` must be `true` for full unattended execution.
- Continue control flow at the orchestrator level by waiting for `phase-6-finalize` to return again; either it returns `status: success` (clean finalize) or another `status: loop_back` (next iteration up to the cap).

**ELSE (default)**:
- Display: `"Loop-back signalled. Run '/plan-marshall action=execute plan={plan_id}' to dispatch the fix tasks."`
- Display: `"After fix tasks complete, run '/plan-marshall action=finalize plan={plan_id}' to re-enter finalize."`
- **STOP**

The conservative default (`loop_back_without_asking == false`) preserves backwards compatibility: existing plans halt and prompt on every loop_back outcome regardless of `finalize_without_asking`. Plans that want full unattended cycles must opt into both knobs.

### Finalize Validation

If finalize requested but tasks incomplete:
```
Cannot finalize: 5 tasks remaining.

Complete all tasks first, then run:
  /plan-marshall plan="jwt-auth" action="finalize"
```
