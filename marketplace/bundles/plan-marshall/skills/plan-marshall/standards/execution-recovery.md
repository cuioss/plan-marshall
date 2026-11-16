# Execution & Finalize Recovery Sub-Procedures

Detailed conditional recovery sub-procedures relocated from `plan-marshall/workflow/execution.md` for progressive disclosure. The orchestrator's execute/finalize skeleton in `execution.md` reaches each of these ONLY when its trigger fires; load and execute the matching section here at that point. All `{placeholder}` tokens carry over from the calling `execution.md` context.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

## Baseline drift recovery (non-zero overlap)

**Trigger**: the just-returned execution-context dispatch is classified `termination-cause == baseline_drift` (`error: baseline_drift`). It arrives on one of two payload routes: the overlap route, carrying `divergent_commits`, `upstream_commit_count` and `conflict_count > 0`; or the declined-probe route, carrying `reconcile_status` (`skipped` | `error`) with its `reason` and `upstream_commit_count` in place of a count (see [`phase-5-execute/standards/sync-with-main.md` § Procedure](../../phase-5-execute/standards/sync-with-main.md#procedure) step 6). Both routes take this recovery — a probe that declined to classify is never read as zero overlap.

**Why this branch handles only non-zero overlap**: phase-5-execute Step 3 invokes `baseline-reconcile` to obtain a deterministic `conflict_count`. When `conflict_count == 0`, phase-5-execute self-absorbs the drift internally — it writes `worktree_sha` + `main_sha` into `status.metadata`, emits a single decision-log entry, and continues its task loop without returning. The orchestrator therefore sees the structured drift TOON ONLY when the upstream commits touch files that overlap with the worktree's in-flight changes — or when the probe declined, which is never treated as zero overlap — and the overlap case is exactly where the request narrative + outline + tasks may no longer be valid against the new baseline. Re-cycling through phase-2-refine and then reconciling the branch onto that baseline (step 4) is the canonical absorption path for this case.

**Unchanged-probe stop — check this BEFORE step 1 of the procedure below.** Compare this drift return's probe against the probe the previous recovery of this plan recorded. The probe is the drift return's own `divergent_commits` list together with its `conflict_count` — the drift TOON carries no conflict file list (see [`phase-5-execute/standards/sync-with-main.md` § Procedure](../../phase-5-execute/standards/sync-with-main.md#procedure) step 6), so those two fields are the whole comparable set. On the non-`success` probe route the TOON carries no `conflict_count` at all, so there the probe is the `reconcile_status` token together with its `reason`.

Both sides record the probe as one `manage-status metadata --set` call (`--field baseline_drift_probe --value {signature}`), where the signature is the entries of `divergent_commits`, in order, `|`-joined, then `:`, then either the conflict count or `{reconcile_status}/{reason}`. (`divergent_commits` is the drift return's `git log --oneline` capture, so an entry is a commit's abbreviated sha together with its subject; joining the entries as they arrive is what makes the signature stable across two probes of the same upstream state.)

- **Signature equal to the recorded one** — the branch and the base have not moved since the previous recovery, so another refine cycle would re-author the same plan and the re-entered execute would return the same drift. STOP on this FIRST repeat, before spending the rest of the cap, and before any of steps 1-3 have run: nothing is logged as a re-dispatch and the persisted phase is left at `5-execute`, exactly where the drift return left it:

  ```toon
  status: error
  error: drift_unchanged
  plan_id: {plan_id}
  display_detail: "baseline drift unchanged since the previous recovery ({divergent_commits}); the branch was not moved onto the new base"
  ```

  This reason means a recovery ran and the drift did not change: the reconcile step did not run or replayed nothing, or upstream churn reproduced the identical probe. The remedy is an operator-confirmed manual reconcile of the worktree branch onto `origin/{base_branch}`; the orchestrator does not try again.
- **Signature different from the recorded one** — overwrite the recorded probe and continue with step 1.

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

      A fetch that fails stops the recovery: log it at ERROR, return an error TOON carrying `error: drift_reconcile_fetch_failed` and the fetch's own failure detail, and do NOT re-enter execute. Reconciling against a base ref that could not be refreshed would leave the branch on a baseline the next Step 3 gate rejects again, and the probe above would report the same drift on the next return.

   2. **Record the pre-rebase head, then rebase onto the new base** through the `git-workflow` verb — never a bare rebase of `origin/{base_branch}`, and never a merge of it:

      ```bash
      git -C {worktree_path} rev-parse HEAD
      python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-rebase-to \
        --plan-id {plan_id} --base {base_branch}
      ```

      `--base` takes the BARE branch name: the verb resolves `origin/{base_branch}` and fetches it again itself before rebasing. That second fetch is idempotent, but it can fail without failing the verb and let the rebase take the stale ref — which is why 4.1 refreshes the ref first and stops on failure, and why this step does not rely on the verb's own fetch for freshness. Keep the head printed above as `{pre_sha}`: the verb reports `pre_sha`/`post_sha` only where it actually reconciled (an already-contained branch's `action: noop`, or a rebase that ran to completion), and the conflict route below needs the pre-rebase head that its payload does not carry.

      The verb also refreshes the worktree's `.plan/execute-script.py` when the replayed commits changed the mapped script set, so the re-entered execute resolves notations against the replayed tree.

      Branch on `status` first, then on `action`:

      - `status: conflict` → 4.3.
      - `status: error` → STOP with the returned error token in place of `drift_reconcile_conflict` (`dirty_worktree`, `detached_head`, `missing_base`, `missing_target`, `rebase_failed`).
      - `status: success` AND `action: rebased` → the rebase replayed commits and moved HEAD; record the outstanding work in 4.2a, then continue at 4.4 with `{post_sha}` from the payload.
      - `status: success` AND `action: noop` → check the marker first (`manage-status metadata --plan-id {plan_id} --get --field baseline_drift_reconcile`):
        - a value starting `pending:` means the branch was already rebased on an attempt that stopped before finishing — the base it contains is that attempt's work, so run 4.4 and 4.5 with the `{pre_sha}:{post_sha}` pair the marker carries, set the marker to `done:` with that pair, and continue at step 5;
        - absent, or starting `done:`, means nothing was rewritten in this attempt or any that reached the marker: skip 4.3-4.5 and continue at step 5.

   2a. **Record the outstanding reconcile before doing anything else with the moved head.** A rebase that moved HEAD leaves two pieces of work a stop can strand — the ledger remap and the publish — and the next attempt sees only an `action: noop` branch that already contains the base. Write both SHAs down first:

       ```bash
       python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
         --plan-id {plan_id} --set \
         --field baseline_drift_reconcile --value "pending:{pre_sha}:{post_sha}"
       ```

       The `noop` branch above reads this field, so a resumed attempt finishes the remap and the publish instead of reading the already-reconciled head as nothing to do. 4.5 sets the same field to `done:{pre_sha}:{post_sha}` once the work is finished. A conflict route that aborts writes no marker: nothing was rewritten.

   3. **Resolve a rebase conflict.** `status: conflict` leaves the rebase in progress with the conflicted paths enumerated in `conflicts[]`. Refine settled the PLAN, not the file content: `baseline-reconcile` emits one `triage` finding per conflicting file whose decision is "re-author the affected scope, or justify in clarifications why the upstream change is irrelevant" — it carries no merged hunk for anyone to apply. Read that decision before authoring anything:

      ```bash
      python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate list \
        --plan-id {plan_id} --phase 2-refine
      ```

      Match each conflicted path to its row by `file_path`; its `resolution` is a token (`fixed`, `taken_into_account`, `rejected`) and the case that applies is stated in that row's `resolution_detail`. A path the list does not carry was never a refine finding and takes the abort route below — do not author content the decision does not cover.

      Author the resolved content HERE, under that decision, and inside this step:

      - where refine re-authored the file's scope, the merged content carries the re-authored intent together with the upstream change it has to coexist with;
      - where refine justified the upstream change as irrelevant to the plan's scope, take the upstream hunk and re-apply the plan's in-flight change on top of it.

      Neither side is discarded wholesale: taking upstream alone silently drops planned work, and keeping the worktree side alone silently drops the upstream commit the drift was about. Record one `decision` log line per resolved path naming what was kept from each side.

      Stage each resolved path with `git -C {worktree_path} add {path}`. `git -C {worktree_path} rebase --continue` refuses to proceed while a conflicted path is still unstaged, so the staging is part of the resolution, not an optional tidy-up. Then continue the rebase with `git -C {worktree_path} rebase --continue`, which is the verb's documented conflict continuation (see [`workflow-integration-git/standards/worktree-handling.md` § The `worktree-rebase-to` Verb](../../workflow-integration-git/standards/worktree-handling.md#the-worktree-rebase-to-verb)). Every raw git command in this item carries `-C {worktree_path}` — the worktree-handling standard forbids relying on the agent's cwd, and a bare `git add` can stage into another checkout's index. A further conflict stops the continuation the same way — repeat this item, including the staging, until the rebase completes.

      When the resolution leaves the replayed commit empty — upstream already carried the planned change, so nothing remains to replay — `--continue` refuses with an empty commit. That is a completed resolution, not a failure: `git -C {worktree_path} rebase --skip` drops the now-empty commit and the loop continues. Only a path that cannot be settled under the refine decision takes the abort route below.

      Once the rebase completes, refresh the worktree's executor — the verb refreshes only on its own successful replay, so a continuation completed here inherits nothing, and upstream commits that added, removed or renamed a bundle script would leave `.plan/execute-script.py` on the pre-rebase notation map:

      ```bash
      python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-executor-refresh \
        --plan-id {plan_id}
      ```

      The verb is non-fatal by contract: a `executor_regenerated: false` is logged with its `executor_detail` and does not abort the reconcile.

      Read the completed head with `git -C {worktree_path} rev-parse HEAD` as `{post_sha}`, record the outstanding reconcile in 4.2a, and continue at 4.4. The remaining conflict set is never left for the execute re-entry to stumble into.

      When a path cannot be settled under the refine decision, enumerate the paths still conflicted — `git -C {worktree_path} diff --name-only --diff-filter=U`, the verb's own method, and the read must happen BEFORE the abort, because `git -C {worktree_path} rebase --abort` resets the index and clears the unmerged set it would otherwise return — log them, abandon the attempt with `git -C {worktree_path} rebase --abort`, and STOP:

      ```toon
      status: error
      error: drift_reconcile_conflict
      conflicts: {the paths enumerated above, before the abort}
      display_detail: "baseline drift reconcile conflicted on {N} paths and the accepted refinement did not settle them"
      ```

      An aborted attempt rewrote nothing — no ledger row is stale and no push is owed.

   4. **Remap the change ledger for the rewritten commits** — only after a rebase that moved HEAD. Every `kind=change` row recorded against a pre-rebase commit is stale, and the phase-5 end-marker guard would report the whole branch unrecorded at the next boundary. Emit the old-to-new map first — no rows are appended — and then consume it (`PLAN-LB-91`'s remap, the same pair `phase-6-finalize`'s `sync-baseline` step runs for its own rebase):

      ```bash
      python3 .plan/execute-script.py plan-marshall:manage-change-ledger:manage-change-ledger remap \
        --worktree-root {worktree_path} --old-head {pre_sha} \
        --emit-map .plan/temp/drift-reconcile-sha-map-{plan_id}.json --dry-run
      python3 .plan/execute-script.py plan-marshall:manage-change-ledger:manage-change-ledger remap \
        --worktree-root {worktree_path} \
        --map-file .plan/temp/drift-reconcile-sha-map-{plan_id}.json
      ```

      `{pre_sha}` and `{post_sha}` are the pair the pending marker carries (recorded in 4.2a) — recorded by the attempt that moved the head. `{pre_sha}`, the head before that rebase, narrows the candidate window to the commits HEAD gained since then. Patch-id decides every match, so a replayed commit that kept its patch maps without help. If either call returns `status: error`, STOP with `drift_reconcile_remap_failed` (logging the returned `error` and `message`): a remap that did not run leaves the ledger stale, and re-entering execute would record work against commits that no longer exist. The pending marker survives that stop, so the next attempt finishes the remap rather than reading the moved head as nothing to do.

      Read the first call's `unmapped` list before continuing. An entry whose stale SHA is an ancestor of `{pre_sha}` belongs to this rebase and its patch changed during conflict resolution: resolve its replacement from `git range-diff --no-color {pre_sha}...{post_sha}`, never from position or `HEAD`, and append that row explicitly — `{deliverable_id}` from the stale ledger row, `{rebased_sha}` from the `range-diff` pair, and `{changed_paths}` from `git diff-tree --no-commit-id --name-only -r {rebased_sha}` (comma-joined), because a conflict resolution can change which paths the replayed commit touches:

      ```bash
      python3 .plan/execute-script.py plan-marshall:manage-change-ledger:manage-change-ledger append \
        --kind change --deliverable-id {deliverable_id} --commit-sha {rebased_sha} \
        --changed-paths {changed_paths} --worktree-root {worktree_path}
      ```

      An `unmapped` entry outside that ancestry belongs to another history — leave it alone. A commit `range-diff` pairs with nothing was dropped by the rebase: report it in the work log and append no row.

   5. **Publish the rewritten branch** when it has a remote counterpart. The rebase rewrote SHAs the remote may already hold, so the push is a `--force-with-lease` through the `git-workflow` branch verb, never a plain force push:

      ```bash
      python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow force-push-with-lease \
        --plan-id {plan_id}
      ```

      `status: success` publishes the rewritten history. A `push_rejected_non_fast_forward` verdict is a lease violation — someone else pushed this branch since the last fetch — and STOPS the recovery with `drift_reconcile_push_lease_violation`: overwriting that history is not this step's decision. Any other `status: error` (`lease_check_failed`, `push_failed`, a pre-push gate refusal) STOPS with `drift_reconcile_push_failed` naming the returned error token, because a remote still holding rewritten-away history is not a state the re-entered execute should run over — the next phase would push a branch that no longer matches it.

      Publish is the last outstanding piece of the reconcile, so it owes the marker's close. Set it once the work is finished — after a successful push, or immediately when the branch was never published and there is nothing on the remote to rewrite:

      ```bash
      python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
        --plan-id {plan_id} --set \
        --field baseline_drift_reconcile --value "done:{pre_sha}:{post_sha}"
      ```

      A plan whose branch was never published has nothing on the remote to rewrite: set the marker `done` and continue at step 5, and the next ordinary push carries the rewritten history.

5. **Re-enter phase-5-execute** via the standard execute-phase envelope in `execution.md`.

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
