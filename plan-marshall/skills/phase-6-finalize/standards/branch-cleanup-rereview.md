# Branch Cleanup — Re-review the Rebased HEAD (trigger A)

Edge-case walkthrough relocated from `branch-cleanup.md` for progressive disclosure. The `branch-cleanup.md` PR-mode flow points here between **Rebase Branch onto Base** and **Pre-Merge Confirmation Gate**; when `state == open` (a rebase + force-push happened), load and execute this section in place, then continue to the Pre-Merge Confirmation Gate. All `{placeholder}` tokens and the `{merge_consent}` / `{hold_start}` state carry over from the calling `branch-cleanup.md` context.

## Re-review the rebased HEAD (trigger A)

**Only if `state == open`** (a rebase + force-push happened above). The rebase/force-push advanced the feature branch HEAD past the `reviewed_commit_sha` of the staged `pr-comment` findings, so the bot reviews on record are stale for the rebased tree — branch-cleanup's own rebase commit is unreviewed. This step re-requests a fresh bot review for the new HEAD and surfaces it through the existing `fetch_findings` → ingest → consolidated-triage pipeline. It uses the SAME `bot_kind`-keyed D2 registry as trigger B — see [`../../automatic-review/SKILL.md`](../../automatic-review/SKILL.md) § "Re-review after a loop-back fix commit (trigger B)" for the registry behavior (trigger-comment mechanics and trigger-time semantics per bot). The trigger fires on the rebased HEAD even when the pre-rebase tree was already reviewed; this is NOT a skip-on-complete-then-move-on.

The gate is the `re_review_on_branch_cleanup` config knob (default `true`) owned by the `plan-marshall:automatic-review` step. Read it from the plan-local execution-manifest step-params snapshot:

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  step-params get --plan-id {plan_id} --phase 6-finalize --step-id plan-marshall:automatic-review
```

Read `re_review_on_branch_cleanup` off the returned `params` object (default: `true`). **When `re_review_on_branch_cleanup == false`**, skip this entire section and proceed to the **Pre-Merge Confirmation Gate**.

**When `re_review_on_branch_cleanup == true`**:

1. Read the most recent **bot-authored** `pr-comment` finding's `bot_kind`. Scan the plan's staged findings from newest to oldest and select the most recent one with a non-empty `bot_kind` — a later human-authored comment (which carries no `bot_kind`) must NOT suppress re-review of an older bot review that went stale after the rebase:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list \
     --plan-id {plan_id} --type pr-comment
   ```

   Walk `findings` newest-first and capture `{bot_kind}` from the first finding whose `bot_kind` is non-empty. If no bot-authored finding exists (the list is empty, or every finding is human-authored), there is no prior bot review to re-trigger — skip this section and proceed to the **Pre-Merge Confirmation Gate**.

2. Resolve the rebased branch's new HEAD SHA and the force-push time:

   ```bash
   git -C {worktree_path} rev-parse HEAD
   ```

   Capture stdout as `{head_sha}`.

   ```bash
   git -C {worktree_path} show -s --format=%cI HEAD
   ```

   Capture stdout as `{push_time}` (the ISO-8601 commit time of the rebased HEAD). It is passed to the registry's required `--push-time` CLI argument for routing uniformity — trigger-time semantics are defined by the registry (see [`workflow-integration-github` SKILL.md § Canonical invocations → `github_re_review re-review`](../../workflow-integration-github/SKILL.md#github_re_review-re-review)).

3. Invoke the D2 re-review registry for the new HEAD. Read `re_review_await_timeout_seconds` off the same `plan-marshall:automatic-review` `params` object returned by the `step-params get` call above (default: 600) and pass it as `--timeout {re_review_await_timeout_seconds}` so the await budget is operator-configurable rather than the hardcoded `DEFAULT_CI_TIMEOUT`. Per-bot trigger-comment mechanics are defined in the registry docs linked above. See [`workflow-integration-github` SKILL.md § Canonical invocations → `github_re_review re-review`](../../workflow-integration-github/SKILL.md#github_re_review-re-review):

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_re_review re-review \
     --pr-number {pr_number} --bot-kind {bot_kind} --head-sha {head_sha} --push-time {push_time} --timeout {re_review_await_timeout_seconds} --plan-id {plan_id}
   ```

   Read both `matched` AND `timed_out` from the returned TOON. **When `matched: true`**, the fresh review is now on the PR. Re-run the consolidated FIND → INGEST → TRIAGE → RESPOND pipeline so the rebase commit is reviewed: call the `fetch_findings` verb (which re-stamps every finding's `reviewed_commit_sha` to the new HEAD and quarantines each body under `raw_input`):

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr \
     fetch_findings --pr-number {pr_number} --plan-id {plan_id}
   ```

   The re-filed findings remain `pending` in the store — `automatic-review` is FIND-only and dispatches no triage of its own (see [`../../automatic-review/SKILL.md`](../../automatic-review/SKILL.md) § "Findings await the unified triage"). They are consumed by the dispatcher-owned unified wait-region triage (`producer=finalize-feedback`), which runs the single batched `manage-findings ingest`, the TOP-LEVEL-only triage, and the `post_responses` RESPOND loop over the union of pending `pr-comment` ∪ `sonar-issue` findings for the rebased HEAD (see [`../SKILL.md`](../SKILL.md) Step 3 item 7c). Log the re-review outcome:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Branch cleanup: re-reviewed rebased HEAD {head_sha} (bot_kind={bot_kind}, matched={matched})"
   ```

   **When `timed_out: true` (and `matched: false`)**, the await budget expired with no fresh bot review for the rebased HEAD — proceed to "On re-review timeout (trigger A)" below instead of falling through to the Pre-Merge Confirmation Gate with an unreviewed HEAD.

### On re-review timeout (trigger A)

This sub-block is evaluated ONLY when the `github_re_review re-review` call above returned `timed_out: true` AND `matched: false` — the await budget (`re_review_await_timeout_seconds`) expired before a fresh bot review landed for the rebased HEAD. Trigger A runs **inline in the orchestrator** (not a dispatched leaf), so the timeout branch fires `AskUserQuestion` directly here (mirroring the budget-exhaustion merge-queue and pre-merge confirmation gates in `branch-cleanup.md`) rather than returning `escalate_ask`.

**Release-before-wait / re-acquire-after (widened hold)**: this trigger-A timeout gate is an operator-wait boundary. Under `merge_hold_window == full_window_release_at_waits`, BEFORE presenting any `AskUserQuestion` below, release the merge mutex if held and FIFO-re-enqueue (`merge_lock release --plan-id {plan_id}`), so the plan does not hold the lock across a human prompt (§ "Merge-Mutex Hold Window" invariant 1 in `branch-cleanup.md`). On the "Wait another {re_review_await_timeout_seconds}s" resume and on any path that continues toward the merge, RE-ACQUIRE via the FIFO poll loop and **re-validate** (`baseline-reconcile`; re-rebase when `origin/{base_branch}` advanced during the released window) before proceeding. The `merge_hold_budget_seconds` bound is checked here too: if the elapsed-since-`{hold_start}` already exceeds the budget, escalate rather than silently continuing to hold. Read `re_review_on_timeout` off the same `plan-marshall:automatic-review` `params` object returned by the `step-params get` call above (default: `ask`) and branch on its value. **Every branch is decision-logged** — a timeout is always an explicit, auditable decision; the `proceed`/"Merge anyway" outcomes log at WARNING naming the unreviewed HEAD SHA.

- **`proceed`** (explicit opt-in to advance the unreviewed HEAD): decision-log at WARNING naming the unreviewed `{head_sha}`, then continue to the **Pre-Merge Confirmation Gate** below (today's silent-proceed, now an explicit, logged choice):

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level WARNING \
    --message "(plan-marshall:phase-6-finalize) Branch cleanup re-review timeout (trigger A): re_review_on_timeout=proceed — advancing UNREVIEWED head_sha={head_sha} to the pre-merge gate after {re_review_await_timeout_seconds}s budget expired"
  ```

- **`defer`** (auto-skip the merge, no prompt): decision-log, then take the SAME skip path as the interactive "No, skip merge" branch in the **Pre-Merge Confirmation Gate** below — set `{merge_consent} = deferred`, skip the **Merge PR**, **Wait for Merge CI**, **Remove Worktree**, and **Switch to Base Branch** sections, emit the `mark-step-done` payload using **Branch C — declined by user**, and return:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level INFO \
    --message "(plan-marshall:phase-6-finalize) Branch cleanup re-review timeout (trigger A): re_review_on_timeout=defer — deferring merge for unreviewed head_sha={head_sha}; re-enter finalize later"
  ```

- **`ask`** (default — fire an inline `AskUserQuestion`): present the three operator choices, mirroring the budget-exhaustion merge-queue prompt style in `branch-cleanup.md`:

  ```text
  AskUserQuestion:
    questions:
      - question: "The re-review of the rebased HEAD timed out with no fresh bot review. How should branch cleanup proceed?"
        header: "Branch Cleanup — Re-review timeout (trigger A)"
        description: |
          **PR**: #{pr_number}
          **Rebased HEAD**: {head_sha} (UNREVIEWED)
          **Await budget**: {re_review_await_timeout_seconds}s (exhausted)

          The bot did not post a fresh review for the rebased HEAD within
          the configured budget. Proceeding to merge would merge an
          unreviewed commit.
        options:
          - label: "Wait another {re_review_await_timeout_seconds}s"
            description: "Re-issue the re-review and await a fresh budget"
          - label: "Merge anyway — proceed unreviewed"
            description: "Advance the unreviewed HEAD to the pre-merge gate"
          - label: "Defer merge"
            description: "Skip the merge; re-enter finalize later"
        multiSelect: false
  ```

  Branch on the operator's selection:

  - **"Wait another {re_review_await_timeout_seconds}s"** → re-enter the inline trigger-A await with a fresh budget. **Re-resolve `{head_sha}` and `{push_time}` FIRST** — the release-before-wait / re-acquire-after boundary above may have re-rebased the branch onto an advanced `origin/{base_branch}` during the released window, advancing HEAD past the `{head_sha}` captured in step 2. Re-issuing the re-review with the stale `{head_sha}` / `{push_time}` would request (and await) a review for a commit the branch no longer points at. So after the re-acquire + re-validate completes, RE-RUN step 2 (`git -C {worktree_path} rev-parse HEAD` → `{head_sha}` and `git -C {worktree_path} show -s --format=%cI HEAD` → `{push_time}`) to capture the CURRENT rebased HEAD, THEN re-issue the `github_re_review re-review` call in step 3 above (with the freshly-resolved `--head-sha {head_sha}` / `--push-time {push_time}` and the same `--timeout {re_review_await_timeout_seconds}`) and re-evaluate `matched`/`timed_out`. Log the decision with the freshly-resolved SHA:

    ```bash
    python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
      decision --plan-id {plan_id} --level INFO \
      --message "(plan-marshall:phase-6-finalize) Branch cleanup re-review timeout (trigger A): user chose to wait another {re_review_await_timeout_seconds}s — re-resolved head_sha={head_sha} (post-reacquisition) and re-issuing re-review"
    ```

  - **"Merge anyway — proceed unreviewed"** → decision-log at WARNING naming the unreviewed `{head_sha}`, then continue to the **Pre-Merge Confirmation Gate** below (same effect as the `proceed` policy):

    ```bash
    python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
      decision --plan-id {plan_id} --level WARNING \
      --message "(plan-marshall:phase-6-finalize) Branch cleanup re-review timeout (trigger A): user chose merge-anyway — advancing UNREVIEWED head_sha={head_sha} to the pre-merge gate"
    ```

  - **"Defer merge"** → take the SAME skip path as the `defer` policy above (set `{merge_consent} = deferred`, skip Merge PR / Wait for Merge CI / Remove Worktree / Switch to Base Branch, emit `mark-step-done` Branch C, return). Log the decision:

    ```bash
    python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
      decision --plan-id {plan_id} --level INFO \
      --message "(plan-marshall:phase-6-finalize) Branch cleanup re-review timeout (trigger A): user chose defer — deferring merge for unreviewed head_sha={head_sha}"
    ```
