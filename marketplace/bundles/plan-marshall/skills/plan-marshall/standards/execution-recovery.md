# Execution & Finalize Recovery Sub-Procedures

Detailed conditional recovery sub-procedures relocated from `plan-marshall/workflow/execution.md` for progressive disclosure. The orchestrator's execute/finalize skeleton in `execution.md` reaches each of these ONLY when its trigger fires; load and execute the matching section here at that point. All `{placeholder}` tokens carry over from the calling `execution.md` context.

## Baseline drift recovery (non-zero overlap)

**Trigger**: the just-returned execution-context dispatch is classified `termination-cause == baseline_drift`. The agent's structured error payload carries `error: baseline_drift` plus `divergent_commits`, `upstream_commit_count`, and `conflict_count > 0`.

**Why this branch handles only non-zero overlap**: phase-5-execute Step 3 invokes `baseline-reconcile` to obtain a deterministic `conflict_count`. When `conflict_count == 0`, phase-5-execute self-absorbs the drift internally — it writes `worktree_sha` + `main_sha` into `status.metadata`, emits a single decision-log entry, and continues its task loop without returning. The orchestrator therefore sees the structured drift TOON ONLY when the upstream commits touch files that overlap with the worktree's in-flight changes, which is exactly the case where the request narrative + outline + tasks may no longer be valid against the new baseline. Re-cycling through phase-2-refine and then reconciling the branch onto that baseline (step 4) is the canonical absorption path for this case.

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

4. **On refine return, bring the branch onto the new base** (the reconcile step). Refine re-authored the plan against the new baseline but moved no ref: its baseline reconciliation is a read-only fetch-and-compare, stated in [`phase-2-refine/standards/refine-workflow-detail.md` § Conflict Handling](../../phase-2-refine/standards/refine-workflow-detail.md#conflict-handling), so the branch still sits on the old base. Re-entering execute without this step runs phase-5-execute Step 3 against the same upstream commits and returns the same drift. Run this step EVERY time refine returns here, before the re-entry in step 5.

   1. **Refresh the base ref in the worktree** — a read-only network round-trip, the same one `phase-5-execute/standards/sync-with-main.md` Step 2 performs:

      ```text
      git -C {worktree_path} fetch origin {base_branch}
      ```

      A fetch that fails stops the recovery: log it at ERROR, return an error TOON carrying `error: drift_reconcile_fetch_failed` and the fetch's own failure detail, and do NOT re-enter execute. Reconciling against a base ref that could not be refreshed would leave the branch on a baseline the next Step 3 gate rejects again, and the probe below would report the same drift.

   2. **Rebase the branch onto the new base** through the `git-workflow` verb — never a bare rebase of `origin/{base_branch}`, and never a merge of it:

      ```bash
      python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-rebase-to \
        --plan-id {plan_id} --base origin/{base_branch}
      ```

      The verb also refreshes the worktree's `.plan/execute-script.py` when the replayed commits changed the mapped script set, so the re-entered execute resolves notations against the replayed tree.

      Read `action`, never `state`: `action: rebased` means the rebase replayed commits and moved HEAD — continue at 4.3; `action: noop` means the branch already contained the new base and nothing was replayed — nothing was rewritten, so skip 4.3 and 4.5 and continue at step 5.

   3. **Resolve a rebase conflict.** A `status: conflict` verdict leaves the rebase in progress with the conflicted paths enumerated in `conflicts[]`. Apply the resolution refine accepted — the iterate-to-confidence loop recorded one resolution per conflicting file as it closed the Q-Gate findings, and those resolutions are the authority. Do NOT author a second, different resolution here. Continue the rebase with `git rebase --continue`, which is the verb's documented conflict continuation (see [`workflow-integration-git/standards/worktree-handling.md` § The `worktree-rebase-to` Verb](../../workflow-integration-git/standards/worktree-handling.md#the-worktree-rebase-to-verb)). When a conflict has no accepted resolution, or the accepted resolutions do not apply cleanly, abandon the attempt with `git rebase --abort`, log the paths, and STOP:

      ```toon
      status: error
      error: drift_reconcile_conflict
      conflicts: {conflicts from the verb}
      display_detail: "baseline drift reconcile conflicted on {N} paths and the accepted refinement did not settle them"
      ```

      A conflict is never left mid-rebase for the execute re-entry to stumble into, and an aborted attempt rewrote nothing — no ledger row is stale and no push is owed. Any other `status: error` verdict (`dirty_worktree`, `detached_head`, `missing_base`, `missing_target`) is the same stop, carrying that verb's error token in place of `drift_reconcile_conflict`.

   4. **Remap the change ledger for the rewritten commits** — only after `action: rebased`. Every `kind=change` row recorded against a pre-rebase commit is stale, and the phase-5 end-marker guard would report the whole branch unrecorded at the next boundary. Emit the old-to-new map first — no rows are appended — and then consume it (`PLAN-LB-91`'s remap, the same pair `phase-6-finalize`'s `sync-baseline` step runs for its own rebase):

      ```bash
      python3 .plan/execute-script.py plan-marshall:manage-change-ledger:manage-change-ledger remap \
        --worktree-root {worktree_path} --old-head {pre_sha} \
        --emit-map .plan/temp/drift-reconcile-sha-map-{plan_id}.json --dry-run
      python3 .plan/execute-script.py plan-marshall:manage-change-ledger:manage-change-ledger remap \
        --worktree-root {worktree_path} \
        --map-file .plan/temp/drift-reconcile-sha-map-{plan_id}.json
      ```

      `{pre_sha}` is the verb's `pre_sha` field — the head before the rebase — which narrows the candidate window to the commits HEAD gained since then. Patch-id decides every match, so a replayed commit that kept its patch maps without help. If either call returns `status: error`, STOP with `drift_reconcile_remap_failed` (logging the returned `error` and `message`): a remap that did not run leaves the ledger stale, and re-entering execute would record work against commits that no longer exist.

      Read the first call's `unmapped` list before continuing. An entry whose stale SHA is an ancestor of `{pre_sha}` belongs to this rebase and its patch changed during conflict resolution: resolve its replacement from `git range-diff --no-color {pre_sha}...{post_sha}`, never from position or `HEAD`, and append that row explicitly with `manage-change-ledger append --kind change --deliverable-id {deliverable_id} --commit-sha {rebased_sha} --changed-paths {paths from the rebased commit} --worktree-root {worktree_path}`. An `unmapped` entry outside that ancestry belongs to another history — leave it alone. A commit `range-diff` pairs with nothing was dropped by the rebase: report it in the work log and append no row.

   5. **Publish the rewritten branch** when it has a remote counterpart. The rebase rewrote SHAs the remote already has, so the push is a `--force-with-lease` through the `git-workflow` branch verb, never a plain force push:

      ```bash
      python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow force-push-with-lease \
        --plan-id {plan_id}
      ```

      A `push_rejected_non_fast_forward` verdict is a lease violation — someone else pushed this branch since the last fetch — and STOPS the recovery with `drift_reconcile_push_lease_violation`: overwriting that history is not this step's decision. A plan whose branch carries no remote counterpart yet skips this push; the next ordinary push carries the rewritten history.

5. **Re-enter phase-5-execute** via the standard execute-phase envelope in `execution.md`.

**Unchanged-probe stop**: before re-dispatching refine (step 3), compare this drift return's probe against the probe the previous recovery of this plan recorded. The probe is the drift return's own `divergent_commits` list together with its `conflict_count` — the drift TOON carries no conflict file list (see [`phase-5-execute/standards/sync-with-main.md` § Procedure](../../phase-5-execute/standards/sync-with-main.md#procedure) step 6), so those two fields are the whole comparable set. On the non-`success` probe route the TOON carries no `conflict_count` at all, so there the probe is the `reconcile_status` token together with its `reason`.

Both sides record the probe as one `manage-status metadata --set` call (`--field baseline_drift_probe --value {signature}`), where the signature is the divergent commit SHAs in order, `|`-joined, then `:`, then either the conflict count or `{reconcile_status}/{reason}`.

- **Signature equal to the recorded one** — the branch and the base have not moved since the previous recovery, so another refine cycle would re-author the same plan and the re-entered execute would return the same drift. STOP on this FIRST repeat, before spending the rest of the cap:

  ```toon
  status: error
  error: drift_unchanged
  plan_id: {plan_id}
  display_detail: "baseline drift unchanged since the previous recovery ({divergent_commits}); the branch was not moved onto the new base"
  ```

  This reason means a recovery ran and the drift did not change: the reconcile step did not run or replayed nothing, or upstream churn reproduced the identical probe. The remedy is an operator-confirmed manual reconcile of the worktree branch onto `origin/{base_branch}`; the orchestrator does not try again.
- **Signature different from the recorded one** — overwrite the recorded probe and continue with step 1.

**Bounded re-dispatch cap**: the orchestrator MUST track a counter for consecutive drift loops on a given plan and refuse to re-dispatch refine when the counter exceeds **3**. The counter is persisted as `manage-status metadata --set --field baseline_drift_count --value {n}` (one call per field) rather than held in session memory, so a resumed orchestrator continues the same bound instead of starting a fresh one. On cap, escalate to the user:

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

The counter resets to zero on any phase-5-execute return that is NOT `baseline_drift` (success, voluntary_checkpoint, budget_yield, verification_handback, error, harness_cancellation, clean_exit_queue_empty all reset it). The recorded `baseline_drift_probe` is cleared with it — a later drift return after a non-drift return is a fresh loop, and comparing it against a probe from a loop that already ended would stop a recovery the branch state no longer justifies.

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

**IF `loop_back_without_asking == true` (default)**:
- Log: `"(plan-marshall:plan-marshall) Config: loop_back_without_asking=true, loop_back_target={target} — auto-continuing"`
- The actual inline dispatch is performed inside `phase-6-finalize/SKILL.md` Step 3 § Loop-back continuation hook (item 7b in the Step 3 dispatch loop). The hook reads `loop_back_target` and routes deterministically:
  - `loop_back_target == "5-execute"`: re-dispatches `Skill: plan-marshall:phase-5-execute --plan-id {plan_id}` against the freshly-allocated fix tasks, then re-enters the finalize FOR loop with the resumable re-entry check skipping already-`done` steps. The hook then transitions `5-execute → 6-finalize` via the standard `plan.phase-6-finalize.finalize_without_asking` gate. When that gate is `false`, the inline cycle halts at the same prompt the forward path uses — so the `5-execute` granularity tier is doubly-gated: both `loop_back_without_asking` AND `finalize_without_asking` must be `true` for full unattended execution.
  - `loop_back_target == "6-finalize"`: skips the phase-5-execute re-dispatch entirely (no `set-phase`, no `Skill: phase-5-execute`), and BREAKs out of the current FOR iteration to RE-ENTER the finalize FOR loop from the start of `manifest.phase_6.steps`. The resumable re-entry check sees the `loop_back`-marked step and re-fires it directly. The `6-finalize` granularity tier is single-gated by `loop_back_without_asking` only — `finalize_without_asking` does not apply because the cycle never leaves `6-finalize`.
- Both branches are capped by `phase-6-finalize.max_iterations` (default 3), counted **per requesting source**: each step that requests a loop-back spends rounds from its own count, whichever granularity tier its loop-back names. Once a step has spent its rounds, a further loop-back from that step is refused and the loop halts even with the flag set; every other step's rounds are untouched. The hook admits each round through `manage-status loop-back admit` (item 7b), which keeps the count.
- Continue control flow at the orchestrator level by waiting for `phase-6-finalize` to return again; either it returns `status: success` (clean finalize) or another `status: loop_back` (the requesting step's next round, up to its cap).

**ELSE (`loop_back_without_asking == false`)**:

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

Setting `loop_back_without_asking == false` selects the interactive shape: a `loop_back` outcome from any phase-6-finalize step halts the dispatcher and prompts the user with the explicit target, eliminating any chance of silent re-routing through `2-refine`. On the auto-continuing default that risk does not arise: the hook re-enters the recorded `loop_back_target` inline, so control never returns to a `/plan-marshall` re-entry where the route resolver could redirect it.

> **Cross-reference**: The full target-phase invariant — including the legal-target enumeration and the granularity rule (`5-execute` for fix-task-required dispositions, `6-finalize` for inline-fixable ones) — lives in `phase-6-finalize/SKILL.md` § "Loop-back continuation hook" → "Two invariants". The assertion above is the dispatcher-level enforcement of that invariant.
