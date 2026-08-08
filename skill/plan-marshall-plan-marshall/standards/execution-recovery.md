# Execution & Finalize Recovery Sub-Procedures

Detailed conditional recovery sub-procedures relocated from `plan-marshall/workflow/execution.md` for progressive disclosure. The orchestrator's execute/finalize skeleton in `execution.md` reaches each of these ONLY when its trigger fires; load and execute the matching section here at that point. All `{placeholder}` tokens carry over from the calling `execution.md` context.

## Baseline drift recovery (non-zero overlap)

**Trigger**: the just-returned execution-context dispatch is classified `termination-cause == baseline_drift`. The agent's structured error payload carries `error: baseline_drift` plus `divergent_commits`, `upstream_commit_count`, and `conflict_count > 0`.

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

4. **On refine return**, re-enter phase-5-execute via the standard execute-phase envelope in `execution.md`.

**Bounded re-dispatch cap**: the orchestrator MUST track a counter for consecutive drift loops on a given plan and refuse to re-dispatch refine when the counter exceeds **3**. On cap, escalate to the user:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR \
  --message "[ERROR] (plan-marshall:plan-marshall) Drift loop cap exceeded (3 consecutive baseline_drift recoveries). Plan requires manual intervention — upstream churn is too high to absorb automatically."
```

Return the orchestrator-level error TOON and STOP:

```toon
status: error
error: drift_loop_cap_exceeded
display_detail: "drift loop cap exceeded after 3 consecutive recoveries"
plan_id: {plan_id}
```

The counter resets to zero on any phase-5-execute return that is NOT `baseline_drift` (success, voluntary_checkpoint, budget_yield, error, harness_cancellation, clean_exit_queue_empty all reset it).

## Loop-back continuation

When `phase-6-finalize` returns with a loop-back signal (`status: loop_back`) — caused by a step recording `outcome: loop_back` with a `loop_back_target` of either `5-execute` (fix-task-required dispositions: FIX with `fix_tasks_created > 0`, `overflow_deferred > 0`) or `6-finalize` (inline-fixable dispositions: SUPPRESS, narrow-rationale ACCEPT, single-annotation FIX) — the orchestrator's behaviour mirrors the forward `finalize_without_asking` shape but is gated by the symmetric reverse-direction knob and routed by the persisted target.

**Config check** — Read `loop_back_without_asking` to determine the next action:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize get --field loop_back_without_asking
```

**Read `loop_back_target` from the most recent `phase_steps["6-finalize"]` outcome record**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read --plan-id {plan_id}
```

The field is structurally guaranteed to be present on every `loop_back` outcome (the manage-status `--loop-back-target` validation contract enforces this — absence is a dispatcher contract bug, not a routing case to handle).

**IF `loop_back_without_asking == true`**:
- Log: `"(plan-marshall:plan-marshall) Config: loop_back_without_asking=true, loop_back_target={target} — auto-continuing"`
- The actual inline dispatch is performed inside `phase-6-finalize/SKILL.md` Step 3 § Loop-back continuation hook (item 7b in the Step 3 dispatch loop). The hook reads `loop_back_target` and routes deterministically:
  - `loop_back_target == "5-execute"`: re-dispatches `Skill: plan-marshall:phase-5-execute --plan-id {plan_id}` against the freshly-allocated fix tasks, then re-enters the finalize FOR loop with the resumable re-entry check skipping already-`done` steps. The hook then transitions `5-execute → 6-finalize` via the standard `plan.phase-6-finalize.finalize_without_asking` gate. When that gate is `false`, the inline cycle halts at the same prompt the forward path uses — so the `5-execute` granularity tier is doubly-gated: both `loop_back_without_asking` AND `finalize_without_asking` must be `true` for full unattended execution.
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
