---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

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

### Orchestrator cwd-pinning (phase-5+)

Per [ADR-002](../../../../../doc/adr/002-Plan-scoped_operations_move_into_a_cwd-pinned_hermetic_worktree.adoc), phases 5 and 6 operate from the plan's own worktree with the orchestrator's working directory pinned to the worktree root. At phase-5 entry the orchestrator performs the atomic move-in by calling the dedicated lifecycle script (deliverable 4), then pins ITS OWN working directory to the path the script returns:

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:prepare_execute prepare \
  --plan-id {plan_id} --branch {worktree_branch} [--base {base_ref}]
```

`prepare_execute.py` materializes the worktree + feature branch, MOVES the plan-scoped non-git state (the plan directory and the executor) into the worktree, and RETURNS the canonical `worktree_path` together with a `status`. It does NOT change the caller's working directory — a subprocess cannot mutate its parent's cwd. The orchestrator reads the returned `worktree_path` and pins its own working directory there for the remainder of phase-5+. From that point the single uniform cwd/worktree-relative rule resolves every `.plan/` lookup to the worktree-resident copy (there is exactly one authoritative copy — main no longer holds it during execution), so no per-phase resolution branch and no reconcile-or-merge step is required. The move-in is atomic-with-rollback (a failed move-in leaves plan state wholly on main) and idempotent (an already-moved plan is a no-op success returning the same path), so a phase-5 re-entry re-pins to the same path without re-moving. The orchestrator returns its working directory to main only at finalize, AFTER the move-back script completes — see § "Finalize Phase" → "Return-to-main ordering" and `phase-6-finalize/SKILL.md`. The worktree-lifecycle and dispatch contract is the central standard at `marketplace/bundles/plan-marshall/skills/workflow-integration-git/standards/worktree-handling.md`; this section documents only the orchestrator's cwd-pinning responsibility and does not re-inline that contract.

**Metrics**: The start of `5-execute` was already recorded by the
`4-plan → 5-execute` fused boundary call emitted at the end of the planning
workflow (see `workflow/planning.md`). When the execute workflow is entered
directly (e.g. via `/plan-marshall action=execute plan={plan_id}` against a
plan already past `4-plan`), use a fused boundary call to close the
previously active phase and start `5-execute` in one step:

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics phase-boundary \
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

The execute phase runs as ONE `execution-context` envelope (dispatched under the `phase-5-execute` role key) that drives the task loop in-context using a simple loop:

```bash
# Get next pending task
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks next --plan-id {plan_id}

# After each step completion, finalize step
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step --plan-id {plan_id} --task-number {task_number} --step {step_number} --outcome done
```

Inside that single envelope, for each task:
1. Read task details via manage-tasks
2. Load `execute-task` in-context as a `Skill:` (leaf-legal in-context skill loading per `dev-agent-behavior-rules` — NOT a per-task `Task:` subagent dispatch) and run the profile-appropriate workflow
3. Mark task complete

The dispatch unit is budget-bounded — neither per-task nor per-deliverable: one envelope runs as many tasks as the per-task budget reserve permits (bundling several small deliverables into one envelope, possibly spanning a single large deliverable across several envelopes), then yields at a TASK boundary on the budget sentinel / `triage_required` / `baseline_drift`, and the orchestrator re-dispatches a fresh envelope to resume the loop until all tasks are done.

### After execution-context returns

After every `execution-context` dispatch returns control to the orchestrator —
whether the agent ran the full execute loop to completion, voluntarily
emitted a "Returning control" line with pending tasks, was cancelled by the
host platform, raised a fatal error, or returned for a reason the
orchestrator cannot classify — the orchestrator MUST record the termination
boundary by calling `manage-metrics record-dispatch-boundary` with parsed
`<usage>` totals and a classified termination cause. The accumulating
artifact at `work/metrics-dispatch-boundaries-5-execute.toon` is the
audit trail that `plan-retrospective` correlates with `[OUTCOME]`-log
coverage gaps to detect agent-initiated re-dispatch.

**Termination-cause classification** — the orchestrator MUST classify every
return into exactly one of the five values below. The detection rules apply
to the agent's terminal payload (text + structured TOON return):

| Cause | Detection rule |
|-------|----------------|
| `task_complete_returned_verbatim` | The agent returned the bare `task_complete` payload from `execute-task` verbatim, without wrapping it in a phase-5-execute terminal payload. (Implies the agent skipped the loop's bookkeeping after a single task.) |
| `voluntary_checkpoint` | The agent emitted any of "Returning control to orchestrator", "progress checkpoint", "partial-completion handoff", or returned a non-error payload while pending tasks remain in the queue. **See "B7 — voluntary_checkpoint no-progress reclassification" below for the deterministic predicate that reclassifies a sub-class of voluntary_checkpoint returns as `error`.** |
| `harness_cancellation` | The dispatch ended with a host-platform cancellation marker (timeout, context-window limit, etc.). |
| `error` | The agent returned a structured error payload via the skill's Error Handling section (including the pending-task-drift fatal error), EXCLUDING the `error_type: baseline_drift` discriminator below. |
| `baseline_drift` | The agent returned `status: error, error_type: baseline_drift` from phase-5-execute Step 3 because `baseline-reconcile` reported `conflict_count > 0` (non-zero overlap between upstream commits and the worktree's in-flight changes). Triggers the **Baseline drift recovery (non-zero overlap)** sub-section below. The zero-overlap case (`conflict_count == 0`) NEVER reaches this branch — phase-5-execute self-absorbs it internally via the metadata-only contract documented in `phase-5-execute/standards/sync-with-main.md` § "Self-absorption contract", then continues its task loop without returning. |
| `clean_exit_queue_empty` | Canonical value for clean exits where the loop drove to completion AND `manage-tasks loop-exit-guard` confirmed the pending queue is empty. The orchestrator MUST classify clean exits as `clean_exit_queue_empty`, NEVER fall back to a non-canonical value — missing or unrecognised causes are recorder-level script errors (the recorder no longer accepts the legacy `unknown` fallback). |

**Script-level pending-count enforcement**: before classifying any return as `clean_exit_queue_empty`, the orchestrator MUST call `python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks loop-exit-guard --plan-id {plan_id}` and confirm it returns `status: success` with `pending_count: 0`. `status: continue` forces re-dispatch — the orchestrator is forbidden from softening this signal. See `manage-tasks/SKILL.md` § "Loop-Exit Guard".

**Bash invocation** — issue the call **before** any subsequent dispatch or
phase-boundary action so the audit trail captures the actual termination
order:

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics record-dispatch-boundary \
  --plan-id {plan_id} --phase 5-execute --termination-cause {voluntary_checkpoint|task_complete_returned_verbatim|harness_cancellation|error|clean_exit_queue_empty} \
  --total-tokens {n} --tool-uses {n} --duration-ms {n}
```

Substitute the `--termination-cause` value with the canonical cause from the
table above and `{n}` with the integer parsed from the agent's
`<usage>...</usage>` block (use `0` when the field is absent).

**B7 — voluntary_checkpoint no-progress reclassification (deterministic)**:

After a dispatch returns and is provisionally classified as `voluntary_checkpoint` per the table above, BEFORE invoking `record-dispatch-boundary`, evaluate the deterministic no-progress predicate:

> `in_progress_count > 0 AND completed_tasks_delta == 0 AND consumed_tokens > 50000`

where:

- `in_progress_count` is the value returned by `manage-tasks loop-exit-guard` for the current iteration.
- `completed_tasks_delta` is the difference between the current iteration's `done` task count and the previous iteration's snapshot (read from the prior `record-dispatch-boundary` row, or `0` on first iteration).
- `consumed_tokens` is the `total_tokens` value parsed from the just-returned agent's `<usage>...</usage>` block (substitute `0` when the field is absent — the threshold then trivially fails and reclassification does NOT fire).

When ALL THREE sub-conditions hold, reclassify `termination_cause` from `voluntary_checkpoint` to `error` BEFORE the `record-dispatch-boundary` call. The reclassification routes the dispatch into the shorter retry-budget / escalation path already coded for `error` (see § "Other Errors" downstream), instead of letting the orchestrator burn additional rounds on a non-progressing loop. Log the reclassification at decision level — the entry MUST carry all three predicate values so retrospective forensic analysis can reconstruct the decision:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-5-execute:no-progress) reclassified voluntary_checkpoint as error — in_progress={N}, completed_delta=0, tokens={X}"
```

When ANY sub-condition fails (in_progress_count==0, OR a task DID complete in the iteration (completed_tasks_delta >= 1), OR consumed_tokens <= 50000), keep the `voluntary_checkpoint` classification as-is — current behaviour is preserved for plans that ARE making progress under the checkpoint flow. The 50K threshold is intentional: it filters out cheap no-op iterations that legitimately bounce off the queue boundary without burning real budget.

The reclassification is a forensic + control-flow decision, not a soft-failure escalation: the dispatch is still recorded via `record-dispatch-boundary` (with `--termination-cause error`), and the orchestrator's downstream `error` handling — including the `error_type` discriminator and the user-facing escalation prompt — runs unchanged.

**Pre-dispatch queue peek** — before issuing any phase-5-execute *re-dispatch* (a dispatch motivated by the prior return classifying as anything other than `clean_exit_queue_empty`, and excluding the human-escalation cases `error` and repeated `harness_cancellation`), the orchestrator MUST first call `manage-tasks loop-exit-guard` as a cheap pre-flight to decide whether the queue is empty. This short-circuits the ~30s envelope dispatch when there is no work left.

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks loop-exit-guard \
  --plan-id {plan_id}
```

Inspect the returned TOON:

- **`status: success` with `pending_count: 0` AND `in_progress_count: 0`** — the queue is empty by the broadened predicate (see `manage-tasks/SKILL.md` § "Loop-Exit Guard"). The orchestrator MUST NOT re-dispatch the execution-context. Instead, synthesize the boundary record with the canonical clean-exit cause (the peek itself is the clean signal — there is no agent return to parse, so token / tool-use / duration counters are recorded as `0`):

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics record-dispatch-boundary \
    --plan-id {plan_id} --phase 5-execute --termination-cause clean_exit_queue_empty \
    --total-tokens 0 --tool-uses 0 --duration-ms 0
  ```

  Then proceed directly to the **Execute Phase Completion** transition (capture invariants for `5-execute`, run the fused `5-execute → 6-finalize` `phase-boundary` call, transition status, and route through the `finalize_without_asking` gate). No phase-5-execute dispatch occurs.

- **`status: continue`** — at least one task is `pending` OR `in_progress`. The broadened predicate (Deliverable 2 of the originating plan) treats both axes as blocking; the `message` field of the guard return names which axis was non-empty so the orchestrator's log surfaces the reason. Proceed with the normal re-dispatch path below.

The peek is the same `loop-exit-guard` verb that the **Boundary-call fence** below uses as its post-classification enforcement. Relocating one invocation to the pre-dispatch decision point lets the orchestrator avoid paying the full envelope cost when the queue is already drained — the structural fix for the empty-queue waste failure mode (two consecutive zero-task dispatches return identical zero-task summaries after a full envelope round-trip).

**Boundary-call fence** — the existing `5-execute → 6-finalize` fused
`phase-boundary` call MUST only fire on a clean exit, defined as
`termination-cause == clean_exit_queue_empty` AND `manage-tasks loop-exit-guard`
returning `status: success` with `pending_count: 0`. For every other
classified cause, the orchestrator MUST re-dispatch the execution-context
(recoverable cases) or escalate to the user (`error` / repeated
`harness_cancellation`) — it MUST NOT transition to `6-finalize` while
pending work remains. This fence is the control-flow analogue of the
Step 12a "Pending-tasks transition guard" in `phase-5-execute` SKILL.md
(which now points to the same `loop-exit-guard` verb as its authoritative
enforcement) and is the structural complement to the script-level `[OUTCOME]`
guard in `manage-tasks finalize-step`.

### Verification-feedback triage (leaf returned triage_required)

**Trigger**: the just-returned phase-5-execute dispatch carries `triage_required: true` in its terminal payload (the leaf detected a verification-failure or quality-gate-failure in Step 11 / Step 11b, persisted each finding to the per-plan Q-Gate store via `manage-findings qgate add`, and returned the signal instead of dispatching). The payload carries `producer` (always `build-runner`) and `finding_type` (`verification-failure` or `quality-gate-failure`). The leaf is a **leaf** — it cannot dispatch `verification-feedback` itself; the orchestrator owns that dispatch. See [`../../ref-workflow-architecture/standards/agents.md`](../../ref-workflow-architecture/standards/agents.md) for the canonical leaf/dispatch-topology contract.

**Handling procedure** (runs in the orchestrator's main context):

1. **Resolve the verification-feedback target** via the role resolver:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
     effort resolve-target --phase phase-5-execute --role verification-feedback
   ```

   Extract the `target` field from the TOON output. Use it as `{target}` in the dispatch and the log line below.

2. **Emit the standardized post-resolve dispatch log line** — see [`../../ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level INFO \
     --message "[DISPATCH] (plan-marshall:phase-5-execute) target={target} level={level} role=verification-feedback workflow=plan-marshall:plan-marshall/workflow/verification-feedback.md plan_id={plan_id}"
   ```

3. **Dispatch `verification-feedback`** as a top-level `Task:` in the main context (the dispatch is by-reference — the subagent queries the per-plan findings store as its first workflow step; the findings are NOT embedded in the prompt):

   ```
   Task: plan-marshall:{target}
     prompt: |
       name: verification-feedback
       plan_id: {plan_id}
       skills[4]:
       - plan-marshall:manage-findings
       - plan-marshall:manage-tasks
       - plan-marshall:manage-architecture
       - plan-marshall:manage-config
       workflow: plan-marshall:plan-marshall/workflow/verification-feedback.md

       producer: build-runner
       caller_phase: phase-5-execute

       WORKTREE: {worktree_path}
   ```

   `caller_phase: phase-5-execute` is the legitimate top-level phase-context field the orchestrator passes for this phase-agnostic workflow (see [`../../extension-api/standards/ext-point-execution-context-workflow.md`](../../extension-api/standards/ext-point-execution-context-workflow.md) § Phase-context propagation for phase-agnostic workflows). The Scope-Deviation Escalation guard lives in [`triage.md`](triage.md) § Step 6.

4. **Consume the triage return** to drive the branch:

   - If `fix_tasks_created > 0` → increment `verify_iteration` in the verification task's metadata, reset the verification task to `pending`, and re-dispatch the execution-context (fix tasks execute before the re-queued verification task via `depends_on`).
   - If `fix_tasks_created == 0` AND `overflow_deferred == 0` → mark the verification task complete (all findings suppressed / accepted / `taken_into_account`); resume the normal post-return classification.
   - If `overflow_deferred > 0` → leave the verification task `pending`; re-fire this triage dispatch on the next phase-5-execute entry (the iteration cap is unchanged).

This dispatch lives in the main-context orchestrator so every cross-envelope `Task:` dispatch originates there, while the leaf retains all deterministic, store-mutating work (failure detection, scope cross-reference, planned-failure exception, iteration-cap check, and `manage-findings qgate add` finding persistence).

### Baseline drift recovery (non-zero overlap)

**Trigger**: the just-returned execution-context dispatch is classified `termination-cause == baseline_drift`. The agent's structured error payload carries `error_type: baseline_drift` plus `divergent_commits`, `upstream_commit_count`, and `conflict_count > 0`.

**Why this branch handles only non-zero overlap**: phase-5-execute Step 3 invokes `baseline-reconcile` to obtain a deterministic `conflict_count`. When `conflict_count == 0`, phase-5-execute self-absorbs the drift internally — it writes `worktree_sha` + `main_sha` into `status.metadata`, emits a single decision-log entry, and continues its task loop without returning. The orchestrator therefore sees the structured drift TOON ONLY when the upstream commits touch files that overlap with the worktree's in-flight changes, which is exactly the case where the request narrative + outline + tasks may no longer be valid against the new baseline. Re-cycling through phase-2-refine is the canonical absorption path for this case.

**Recovery procedure**:

1. **Log the drift to work-log**:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level ERROR \
     --message "[STATUS] (plan-marshall:plan-marshall) Baseline drift recovery: {upstream_commit_count} upstream commits with {conflict_count} conflicting files. Divergent: {divergent_commits}. Re-dispatching phase-2-refine."
   ```

2. **Reset the persisted phase to `2-refine`** so the orchestrator's standard envelope re-enters refine cleanly:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-status:manage-status set-phase \
     --plan-id {plan_id} --phase 2-refine
   ```

3. **Re-dispatch phase-2-refine using the standard envelope** from `workflow/planning.md` (no new fields, no `loop_back` discriminator — refine sees standard full-cycle re-entry; baseline reconciliation is its Step 3d responsibility):

   See `plan-marshall/workflow/planning.md` § "2-Refine Phase" for the canonical dispatch envelope. The orchestrator MUST use that envelope verbatim — no additional inputs propagate the drift signal to refine, because the upstream commits are already visible to `baseline-reconcile` on refine entry.

4. **On refine return**, re-enter phase-5-execute via the standard execute-phase envelope earlier in this document.

**Bounded re-dispatch cap**: the orchestrator MUST track a counter for consecutive drift loops on a given plan and refuse to re-dispatch refine when the counter exceeds **3**. On cap, escalate to the user:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR \
  --message "[ERROR] (plan-marshall:plan-marshall) Drift loop cap exceeded (3 consecutive baseline_drift recoveries). Plan requires manual intervention — upstream churn is too high to absorb automatically."
```

Return the orchestrator-level error TOON and STOP:

```toon
status: error
error_type: drift_loop_cap_exceeded
display_detail: "drift loop cap exceeded after 3 consecutive recoveries"
plan_id: {plan_id}
```

The counter resets to zero on any phase-5-execute return that is NOT `baseline_drift` (success, voluntary_checkpoint, error, harness_cancellation, clean_exit_queue_empty all reset it).

**No `loop_back` field**: this branch deliberately does NOT introduce a `loop_back` input on the phase-2-refine dispatch envelope. The orchestrator's existing phase-6-finalize → phase-5-execute loop-back routing is unrelated and remains the single owner of that field-shape. Drift recovery uses standard `set-phase` + dispatch, which is structurally simpler.

**Cross-references**:
- `phase-5-execute/SKILL.md` Step 3 — the deterministic drift detection that produces the structured TOON this branch consumes
- `phase-5-execute/standards/sync-with-main.md` § "Self-absorption contract" — the zero-overlap case that NEVER reaches this branch
- `plan-marshall/workflow/planning.md` § "2-Refine Phase" — the standard refine dispatch envelope this branch reuses

### Execute Phase Completion

After all tasks complete, transition and check auto-continue:

**Metrics**: During the task loop, maintain a running sum of `total_tokens`,
`tool_uses`, and `duration_ms` from each task agent's `<usage>` tag. The
canonical sub-agent `<usage>` token key is `total_tokens` — emitters MUST use
that key (the `manage-metrics enrich` parser also tolerates the
`subagent_tokens` alias as a recovery fallback, but `total_tokens` is
canonical). After all tasks complete, record the `5-execute → 6-finalize`
boundary in a single fused call (forwarding the aggregated totals to the
closing phase):
```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics phase-boundary \
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
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status transition \
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
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics phase-boundary \
  --plan-id {plan_id} --prev-phase {prev_phase} --next-phase 6-finalize
```

**Phase handshake** (direct-entry variant): capture the just-closed `{prev_phase}` phase. When entering after the execute workflow already captured `5-execute`, this is idempotent — `capture` upserts the row.

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake capture \
  --plan-id {plan_id} --phase {prev_phase}
```

The preceding `manage-status transition --completed 5-execute` call refuses to advance and returns the drift TOON when the captured `5-execute` invariants diverge from live state — no separate verify step is required at this boundary. (The transition verb inlines `phase_handshake verify --phase 5-execute --strict` whenever the next phase is in `_BLOCKING_BOUNDARIES`. The standalone `phase_handshake verify` script remains available for retrospective / diagnostic use.)

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:plan-marshall) Loading plan-marshall:phase-6-finalize"
```

Resolve the current Claude Code `session_id` from the plan's status metadata before dispatching the skill. The `session capture` operation (run at plan-init time by the platform-runtime `SessionStart` hook) stored it there. Pass it alongside `plan_id` so `default:record-metrics` can call `manage-metrics enrich` on the live plan directory before `default:archive-plan` moves it.

**Resolve `session_id`:**

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} --get --field session_id
```

Parse `value` from the TOON output.

**On `status: error` or empty `value`** — do NOT abort immediately. The session may still be live, so attempt exactly one late session capture before falling back to the hard-block:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session capture \
  --plan-id {plan_id}
```

Then re-read `status.metadata.session_id`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
  --plan-id {plan_id} --get --field session_id
```

- **Late capture succeeded** (`status: success` and `value` now populated): use the captured value as the resolved `session_id` and proceed with the dispatch below.
- **Late capture also failed** (`status: error` or `value` still empty): abort the finalize phase with a clear message — do **not** invent a filler value and do **not** reach for any `$VAR` expansion. See `phase-6-finalize/SKILL.md` → "How to obtain session_id" for the full resolver contract and forbidden patterns.

The retry runs at most once — never loop the capture call.

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

When `phase-6-finalize` returns with a loop-back signal (`status: loop_back`) — caused by a step recording `outcome: loop_back` with a `loop_back_target` of either `5-execute` (fix-task-required dispositions: FIX with `fix_tasks_created > 0`, `overflow_deferred > 0`) or `6-finalize` (inline-fixable dispositions: SUPPRESS, narrow-rationale ACCEPT, single-annotation FIX) — the orchestrator's behaviour mirrors the forward `finalize_without_asking` shape but is gated by the symmetric reverse-direction knob and routed by the persisted target.

**Config check** — Read `loop_back_without_asking` to determine the next action:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize get --field loop_back_without_asking --audit-plan-id {plan_id}
```

**Read `loop_back_target` from the most recent `phase_steps["6-finalize"]` outcome record**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read --plan-id {plan_id}
```

The field is structurally guaranteed to be present on every `loop_back` outcome (the manage-status `--loop-back-target` validation contract enforces this — absence is a dispatcher contract bug, not a routing case to handle).

**IF `loop_back_without_asking == true`**:
- Log: `"(plan-marshall:plan-marshall) Config: loop_back_without_asking=true, loop_back_target={target} — auto-continuing"`
- The actual inline dispatch is performed inside `phase-6-finalize/SKILL.md` Step 3 § Loop-back continuation hook (item 7b in the Step 3 dispatch loop). The hook reads `loop_back_target` and routes deterministically:
  - `loop_back_target == "5-execute"`: re-dispatches `Skill: plan-marshall:phase-5-execute --plan-id {plan_id}` against the freshly-allocated fix tasks, then re-enters the finalize FOR loop with the resumable re-entry check skipping already-`done` steps. The hook then transitions `5-execute → 6-finalize` via the standard `phase-5-execute.finalize_without_asking` gate. When that gate is `false`, the inline cycle halts at the same prompt the forward path uses — so the `5-execute` granularity tier is doubly-gated: both `loop_back_without_asking` AND `finalize_without_asking` must be `true` for full unattended execution.
  - `loop_back_target == "6-finalize"`: skips the phase-5-execute re-dispatch entirely (no `set-phase`, no `Skill: phase-5-execute`), and BREAKs out of the current FOR iteration to RE-ENTER the finalize FOR loop from the start of `manifest.phase_6.steps`. The resumable re-entry check sees the `loop_back`-marked step and re-fires it directly. The `6-finalize` granularity tier is single-gated by `loop_back_without_asking` only — `finalize_without_asking` does not apply because the cycle never leaves `6-finalize`.
- Both branches are capped by `phase-6-finalize.max_iterations` (default 3, counted across BOTH granularity tiers); beyond that the loop halts and prompts the user even with the flag set.
- Continue control flow at the orchestrator level by waiting for `phase-6-finalize` to return again; either it returns `status: success` (clean finalize) or another `status: loop_back` (next iteration up to the cap).

**ELSE (default)**:

**Persisted-phase assertion (loopback target invariant)** — before displaying any user-facing prompt, assert that the persisted `current_phase` matches the recorded `loop_back_target`:

- When `loop_back_target == "5-execute"`, the persisted `current_phase` MUST equal `5-execute` (the loop-back-emitting step issued `manage-status set-phase --phase 5-execute` before its terminal `mark-step-done`).
- When `loop_back_target == "6-finalize"`, the persisted `current_phase` MUST equal `6-finalize` (the loop-back-emitting step did NOT issue `set-phase`).

When the assertion fails, log `[STATUS] (plan-marshall:plan-marshall) Loop-back target invariant violated: persisted phase={persisted}, expected={loop_back_target}` and **STOP** without displaying the user-facing prompts. Do NOT fall through to the prompt block. This eliminates the silent route-resolver redirect to `2-refine` that would otherwise occur when the user re-enters `/plan-marshall` after the persisted phase has drifted.

**When the assertion passes** — display the explicit user prompt, named for the recorded target:

- IF `loop_back_target == "5-execute"`:
  - Display: `"Loop-back signalled. Run '/plan-marshall action=execute plan={plan_id}' to dispatch the fix tasks."`
  - Display: `"After fix tasks complete, run '/plan-marshall action=finalize plan={plan_id}' to re-enter finalize."`
- IF `loop_back_target == "6-finalize"` (inline replay — hybrid-contract path):
  - Display: `"Loop-back signalled (inline replay). Run '/plan-marshall action=finalize plan={plan_id}' to replay the finalize step."`

In both branches, append a third line clarifying the precise target so the user can audit the routing decision:

- Display: `"Loop-back target: {5-execute | 6-finalize} (per the most recent finalize-step outcome)."`

Then **STOP**.

The conservative default (`loop_back_without_asking == false`) preserves the conservative interactive shape: a `loop_back` outcome from any phase-6-finalize step halts the dispatcher and prompts the user with the explicit target, eliminating any chance of silent re-routing through `2-refine`. Plans that want full unattended cycles must opt into both `loop_back_without_asking` AND `finalize_without_asking`.

> **Cross-reference**: The full target-phase invariant — including the legal-target enumeration and the granularity rule (`5-execute` for fix-task-required dispositions, `6-finalize` for inline-fixable ones) — lives in `phase-6-finalize/SKILL.md` § "Loop-back continuation hook" → "Two invariants". The assertion above is the dispatcher-level enforcement of that invariant.

### Finalize Validation

If finalize requested but tasks incomplete:
```
Cannot finalize: 5 tasks remaining.

Complete all tasks first, then run:
  /plan-marshall plan="jwt-auth" action="finalize"
```

## Output

Top-level orchestrator workflow. Conformance to the ext-point output contract:

```toon
status: success | error
display_detail: "<plan {plan_id} reached {terminal_phase}>"
```

The orchestrator emits this shape when wrapped in a `Task: execution-context-{level}` dispatch. When entered interactively, progress is surfaced via `manage-logging` records on each phase boundary; the terminal user-facing message replaces the TOON.
