# Branch Cleanup — Re-review the Rebased HEAD (trigger A)

Edge-case walkthrough relocated from `branch-cleanup.md` for progressive disclosure. The `branch-cleanup.md` PR-mode flow points here between **Rebase Branch onto Base** and **Pre-Merge Confirmation Gate**; load and execute this section in place under the entry condition that section states — `state == open` AND the rebase actually advanced HEAD — then continue to the Pre-Merge Confirmation Gate. **The entry condition is owned by the caller, not restated here**, so a change to the rebase routing cannot leave this document asserting a condition the caller no longer applies. All `{placeholder}` tokens and the `{merge_consent}` / `{hold_start}` state carry over from the calling `branch-cleanup.md` context — and so does the closed merge-dispatch set defined in [`branch-cleanup.md`](branch-cleanup.md) § "Merge routing (`use_merge_queue`)" → "The dispatch set is CLOSED", which owns it: **no merge-shaped `ci pr` dispatch may be issued from this document at all.** This walkthrough runs before the merge routing and only ever advances, defers, or re-awaits; every merge-shaped dispatch belongs to the owning section, so consult it there rather than reading any branch here as a licence to merge.

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this walkthrough's two decision calls — `github_re_review re-review` and `github_pr fetch_findings` — are not `manage-*`, and they are precisely the calls that decide whether the rebased HEAD was reviewed at all.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than looking for a fixed field list: beyond `status` and `error` the diagnostic fields vary by verb — `ci` verbs carry `operation`, `error_cause`, and `context`, the plan-resolution envelopes carry `message` and `plan_id` instead, and neither list is exhaustive. `error` is sometimes a hard-coded generic string whose real cause sits in one of the other fields, so dropping them can discard the cause entirely. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return — the envelope's diagnostic fields are not success payload, and dropping any of them leaves the step reporting a failure with no cause. A malformed or truncated stdout that carries **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause. There is no envelope to preserve on that sub-path — synthesize the error TOON instead, naming the call (notation, subcommand, and arguments) and carrying the raw stdout verbatim as the only account of the cause that exists. Here that means an absent `matched` / `head_sha_verified` pair is an **unread** re-review, never a `matched: false`.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

This document carries NO step-activation logic. It is loaded and executed in place by `branch-cleanup.md` under the entry condition that document owns.

## Re-review the rebased HEAD (trigger A)

Reached only under the caller's entry condition (see the note above): `state == open` AND a rebase that actually advanced HEAD. That advance moved the feature branch past the `reviewed_commit_sha` of the staged `pr-comment` findings, so the bot reviews on record are stale for the rebased tree — branch-cleanup's own rebase commit is unreviewed. This step re-requests a fresh bot review for the new HEAD and surfaces it through the existing `fetch_findings` → ingest → consolidated-triage pipeline. It uses the SAME `bot_kind`-keyed D2 registry as trigger B — see [`../../automatic-review/SKILL.md`](../../automatic-review/SKILL.md) § "Re-review after a loop-back fix commit (trigger B)" for the registry behavior (trigger-comment mechanics and trigger-time semantics per bot). Once entered, the trigger fires on the rebased HEAD **even when the pre-rebase tree was already reviewed** — this is NOT a skip-on-complete-then-move-on. That is a statement about a run whose HEAD advanced; it is not a licence to enter when it did not, which the caller's condition governs.

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

   Read `matched`, `timed_out`, **and `head_sha_verified`** from the returned TOON. The last is load-bearing and MUST be consulted: `await_fresh_review` matches on EITHER the **review** signal (`head_sha_verified: true`) OR the **issue comment** signal (`head_sha_verified: false`). The two match conditions are stated ONCE, by the producer — see [`workflow-integration-github` SKILL.md § Workflow 3](../../workflow-integration-github/SKILL.md#workflow-3-re-review-after-a-head-advancing-branch-operation) signal table; do not restate them here, because a copy left behind is a consumer acting on a predicate the producer no longer implements. Only the review signal is a review of this HEAD; the comment signal is the bot answering **without** naming the commit it reviewed. Reading `matched` alone credits a review that never happened — the incremental-review decline this step exists to catch.

   - **When `matched: true` AND `head_sha_verified: true`**, the fresh review of `{head_sha}` is now on the PR. Re-run the consolidated FIND → INGEST → TRIAGE → RESPOND pipeline so the rebase commit is reviewed: call the `fetch_findings` verb (which re-stamps every finding's `reviewed_commit_sha` to the new HEAD and quarantines each body under `raw_input`):

     ```bash
     python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr \
       fetch_findings --pr-number {pr_number} --plan-id {plan_id}
     ```

     The re-filed findings remain `pending` in the store — `automatic-review` is FIND-only and dispatches no triage of its own (see [`../../automatic-review/SKILL.md`](../../automatic-review/SKILL.md) § "Findings await the unified triage"). They are consumed by the dispatcher-owned unified wait-region triage (`producer=finalize-feedback`), which runs the single batched `manage-findings ingest`, the TOP-LEVEL-only triage, and the `post_responses` RESPOND loop over the union of pending `pr-comment` ∪ `sonar-issue` findings for the rebased HEAD (see [`../SKILL.md`](../SKILL.md) Step 3 item 7c). Log the re-review outcome:

     ```bash
     python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
       work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Branch cleanup: re-reviewed rebased HEAD {head_sha} (bot_kind={bot_kind}, head_sha_verified=true)"
     ```

   - **When `matched: true` AND `head_sha_verified: false`**, the bot answered the re-review with a comment that names **no** reviewed-commit SHA — an **incremental-review decline**. It did NOT review `{head_sha}`, so this is **not** a completed re-review and MUST NOT be treated as one. Add `{bot_kind}` to the accumulating `{declined_bots}` set (a comma-joined bot_kind list carried forward to the Pre-Merge Review-Completeness Barrier's `--declined-bots`, where it resolves to the blocking `declined` state), log the decline, and proceed to "On re-review timeout (trigger A)" below — re-triggering a bot that just declined produces another decline, so the decline takes the same disposition path as a timeout (proceed-with-authorization / defer / ask) rather than looping the trigger:

     ```bash
     python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
       work --plan-id {plan_id} --level WARNING --message "[WARNING] (plan-marshall:phase-6-finalize) Branch cleanup: re-review of rebased HEAD {head_sha} returned a comment with no reviewed-commit SHA (head_sha_verified=false, bot_kind={bot_kind}) — recorded as declined, NOT a completed review"
     ```

   - **When `timed_out: true` (and `matched: false`)**, the await budget expired with no fresh bot review for the rebased HEAD — proceed to "On re-review timeout (trigger A)" below instead of falling through to the Pre-Merge Confirmation Gate with an unreviewed HEAD.

### On re-review timeout (trigger A)

This sub-block is evaluated on exactly TWO entrants from the `github_re_review re-review` call above, and on nothing else. The two items below state that ENTRY CONDITION — which returns reach this block — and neither is an outcome arm: they carry no disposition of their own, and every branch further down applies to both.

- Entrant 1, the timeout — **`timed_out: true` AND `matched: false`**: the await budget (`re_review_await_timeout_seconds`) expired before a fresh bot review landed for the rebased HEAD.
- Entrant 2, the decline — **`matched: true` AND `head_sha_verified: false`**: the incremental-review decline the bullet above routes here; the bot answered, but its answer named no reviewed-commit SHA, so it did not review the rebased HEAD.

⛔ **Both entrants, not the timeout alone.** An entry condition naming only the timeout is what made the decline arm's routing unreachable as written: the bullet above sends a decline into this block while a condition scoped to `timed_out: true` AND `matched: false` rejects the very case it was handed. The two share this disposition path for the reason that bullet states — re-triggering a bot that just declined produces another decline, exactly as re-triggering after a timeout produces another timeout — so every branch below applies to both unchanged.

**Resolve `{outcome}` and `{outcome_detail}` ONCE here, from the entrant that reached this block.** Sharing a disposition path is not sharing an observation: only one of the two entrants expired a budget. Every branch below — decision-log line, `AskUserQuestion` prompt, and persisted `--granted-over` string alike — renders these rather than restating a budget expiry:

| Entrant | `{outcome}` | `{outcome_detail}` |
|---------|-------------|--------------------|
| 1, the timeout (`timed_out: true` AND `matched: false`) | `timed_out` | `no fresh bot review landed for this HEAD within the {re_review_await_timeout_seconds}s budget` |
| 2, the decline (`matched: true` AND `head_sha_verified: false`) | `declined` | `DECLINED by {declined_bots} — the bot answered without naming a reviewed commit, so no budget expired` |

⛔ **Never restate the timeout wording on a branch that both entrants reach.** A decline recorded as a budget expiry is a false claim in the decision log, in the operator prompt, and — worst of the three — in the persisted authorization record, which outlives the run and is what an audit reads to learn WHICH gap the operator accepted.

Trigger A runs **inline in the orchestrator** (not a dispatched leaf), so this gate fires `AskUserQuestion` directly here (mirroring the budget-exhaustion merge-queue and pre-merge confirmation gates in `branch-cleanup.md`) rather than returning `escalate_ask`.

**Release-before-wait / re-acquire-after (widened hold)**: this trigger-A timeout gate is an operator-wait boundary. Under `merge_hold_window == full_window_release_at_waits`, BEFORE presenting any `AskUserQuestion` below, release the merge mutex if held and FIFO-re-enqueue (`merge_lock release --plan-id {plan_id}`), so the plan does not hold the lock across a human prompt (§ "Merge-Mutex Hold Window" invariant 1 in `branch-cleanup.md`). On the "Wait another {re_review_await_timeout_seconds}s" resume and on any path that continues toward the merge, RE-ACQUIRE via the FIFO poll loop and **re-validate** (`baseline-reconcile`; re-rebase when `origin/{base_branch}` advanced during the released window) before proceeding. The `merge_hold_budget_seconds` bound is checked here too: if the elapsed-since-`{hold_start}` already exceeds the budget, escalate rather than silently continuing to hold. Read `re_review_on_timeout` off the same `plan-marshall:automatic-review` `params` object returned by the `step-params get` call above (default: `ask`) and branch on its value. **Every branch is decision-logged** — advancing an unreviewed HEAD is always an explicit, auditable decision, whichever entrant reached here; the `proceed`/"Merge anyway" outcomes log at WARNING naming the unreviewed HEAD SHA and the resolved `{outcome}`.

Both branches that advance an unreviewed HEAD — the `proceed` policy branch and the `ask` → "Merge anyway — proceed unreviewed" selection — additionally **grant** a `rereview-timeout-override` bound to `{head_sha}` and to the gap class `rereview-timeout`. The decision-log line is the honest record of the ruling; it is not, and never becomes, admissible evidence at the pre-merge barrier. Neither is the grant itself: this gate runs BEFORE the pre-merge review barrier and at the same HEAD, and its `--gap-class rereview-timeout` is what keeps it from being read as authorization there — the barrier checks for `review-barrier-gap` and this ruling covers a different gap. See `branch-cleanup.md` § "Merge-Authorization Roster" for the full population, § "Gap classes — why HEAD-binding alone is not authorization" for why the class is required, and § "Authorization check — the only admissible evidence on a blocked path" for where these grants are checked.

- **`proceed`** (explicit opt-in to advance the unreviewed HEAD): decision-log at WARNING naming the unreviewed `{head_sha}`, **then persist the ruling as a HEAD-bound authorization**, then continue to the **Pre-Merge Confirmation Gate** below (today's silent-proceed, now an explicit, logged choice):

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level WARNING \
    --message "(plan-marshall:phase-6-finalize) Branch cleanup re-review timeout (trigger A): re_review_on_timeout=proceed — advancing UNREVIEWED head_sha={head_sha} to the pre-merge gate; outcome={outcome} — {outcome_detail}"
  ```

  The log line names `{head_sha}` but persists nothing, so the pre-merge barrier cannot read it as evidence. Grant the authorization against that same `{head_sha}`, and render `{outcome_detail}` into `--granted-over` so the persisted record says which gap was accepted rather than assuming the timeout one (see `manage-status` Canonical invocations → `merge-authorization — grant`):

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-status:manage-status merge-authorization grant \
    --plan-id {plan_id} --kind rereview-timeout-override --head {head_sha} --gap-class rereview-timeout \
    --granted-over "unreviewed HEAD: {outcome_detail}" --reason "re_review_on_timeout=proceed policy branch (outcome={outcome})"
  ```

- **`defer`** (auto-skip the merge, no prompt): decision-log, then take the SAME skip path as the interactive "No, skip merge" branch in the **Pre-Merge Confirmation Gate** below — set `{merge_consent} = deferred`, skip the **Merge PR**, **Wait for Merge CI**, **Remove Worktree**, and **Switch to Base Branch** sections, emit the `mark-step-done` payload using **Branch C — declined by user**, and return:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level INFO \
    --message "(plan-marshall:phase-6-finalize) Branch cleanup re-review timeout (trigger A): re_review_on_timeout=defer — deferring merge for unreviewed head_sha={head_sha}; re-enter finalize later"
  ```

- **`ask`** (default — fire an inline `AskUserQuestion`): present the three operator choices, mirroring the budget-exhaustion merge-queue prompt style in `branch-cleanup.md`:

  ⛔ **The prompt names `{outcome_detail}`, never a hard-coded budget expiry.** Both entrants reach this prompt and the operator is choosing on the strength of what was observed: a timeout means nothing answered, a decline means the bot answered without reviewing this HEAD. Rendering the timeout wording on a decline hands the operator a claim nothing made, and the "wait" option is the WEAKEST of the three there — no budget expired, so a longer one buys nothing, and a bot that declined this HEAD answers a re-trigger with another decline rather than a review. Say so in the option's description on that entrant instead of silently offering it as equal.

  ```text
  AskUserQuestion:
    questions:
      - question: "The re-review of the rebased HEAD did not produce a review of that HEAD ({outcome}). How should branch cleanup proceed?"
        header: "Branch Cleanup — Re-review unresolved (trigger A)"
        description: |
          **PR**: #{pr_number}
          **Rebased HEAD**: {head_sha} (UNREVIEWED)
          **Outcome**: {outcome} — {outcome_detail}

          No bot review of the rebased HEAD is on record. Proceeding to
          merge would merge an unreviewed commit.
        options:
          - label: "Wait another {re_review_await_timeout_seconds}s"
            description: "Re-issue the re-review and await a fresh budget (weakest option on outcome=declined: the bot already answered)"
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

    This branch grants nothing — it awaits a review rather than authorizing an unreviewed advance. Because it re-resolves `{head_sha}` before re-issuing, a `rereview-timeout-override` granted on a SUBSEQUENT pass through this gate is bound to the re-resolved HEAD, not the stale one captured before the wait.

  - **"Merge anyway — proceed unreviewed"** → decision-log at WARNING naming the unreviewed `{head_sha}`, **then persist the ruling as a HEAD-bound authorization**, then continue to the **Pre-Merge Confirmation Gate** below (same effect as the `proceed` policy):

    ```bash
    python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
      decision --plan-id {plan_id} --level WARNING \
      --message "(plan-marshall:phase-6-finalize) Branch cleanup re-review timeout (trigger A): user chose merge-anyway — advancing UNREVIEWED head_sha={head_sha} to the pre-merge gate; outcome={outcome} — {outcome_detail}"
    ```

    ```bash
    python3 .plan/execute-script.py plan-marshall:manage-status:manage-status merge-authorization grant \
      --plan-id {plan_id} --kind rereview-timeout-override --head {head_sha} --gap-class rereview-timeout \
      --granted-over "unreviewed HEAD: {outcome_detail}" --reason "{operator selection: Merge anyway — proceed unreviewed} (outcome={outcome})"
    ```

  - **"Defer merge"** → take the SAME skip path as the `defer` policy above (set `{merge_consent} = deferred`, skip Merge PR / Wait for Merge CI / Remove Worktree / Switch to Base Branch, emit `mark-step-done` Branch C, return). Log the decision:

    ```bash
    python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
      decision --plan-id {plan_id} --level INFO \
      --message "(plan-marshall:phase-6-finalize) Branch cleanup re-review timeout (trigger A): user chose defer — deferring merge for unreviewed head_sha={head_sha}"
    ```
