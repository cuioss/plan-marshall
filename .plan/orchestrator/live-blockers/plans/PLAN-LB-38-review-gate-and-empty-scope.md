# PLAN-LB-38: An empty change list runs tests, and the review gate passes only on a finished review

epic: live-blockers
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-38-review-gate-and-empty-scope.md` and is queued as one row file, `queue/PLAN-LB-38.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on 2026-10-11 by operator instruction ("create a plan for fixing both and emit it now"),
> from two Open Defects of this epic: the empty `--changed-paths` fail-open PLAN-LB-33 introduced,
> and the nine review-gate defects left unowned after PLAN-LB-24. OBSERVED claims were read at
> `370f42379` or `7dd1d3433` by read-only reviews on 2026-10-10, except where marked; `main` is at
> `2fd164ec9`. Re-read every cited line at outline: line numbers may have moved.

> WEAK MERGE. Part A (deliverable 1) and part B (deliverables 2–10) share no file. They are one
> plan by operator instruction, and because each landing in this epic costs 7 to 15 million tokens,
> most of it in finalize. Part A is small and should be done first; the outline may split the plan
> along the line between deliverables 1 and 2 if part B's outline grows beyond one plan.

## Objective

**Part A.** A dispatched task decides which tests to run through `resolve-test-scope
--changed-paths {changed_paths}`. Since PLAN-LB-33 (#1745) made the executor keep an empty option
value, an empty `--changed-paths ""` becomes an empty footprint, which reads as a resolvable change
that touches nothing — so the task runs no test and reports its verification as passed. Before
#1745 the same call failed loudly. The surrounding code already fails toward the whole tree when
the footprint cannot be resolved; an empty argument must take that route too, never "nothing
changed".

**Part B.** The automatic-review step decides whether a pull request has been reviewed by every
required bot. Two of its defects can let a merge through on a review that has not happened; four
make the step stall until someone intervenes by hand, as on #1742 and #1745; two cost manual
triage on every pass; one is a missing pre-flight check. This plan makes the gate credit only a
finished review of the head, recover a required bot by itself, and stop filing the bots'
acknowledgments as findings.

## Deliverables

### Part A — the empty change list

1. **An empty change list never resolves to "no tests".** In `resolve-test-scope`, an empty or
   whitespace-only `--changed-paths` value is refused (`status: error`,
   `error: empty_changed_paths`, naming the flag) or resolved as the whole-tree fallback the
   unresolvable branch already uses — the outline picks one and records why; it must not read as
   an empty footprint. A task whose real change set is empty is not served by passing `""`: the
   outline settles how such a task is represented (for example omitting the flag and passing the
   plan id) so the refusal does not break it. Do the same for `architecture resolve
   --narrow-unit ""`, which today falls back to the module-wide resolve without `bound_source`.
   `execute-task/SKILL.md` Step 5(b) states what the leaf does when its change list is empty.
   *Done when:* tests show `--changed-paths ""` and `--changed-paths " , "` never return
   `divergence_possible: false`; `--narrow-unit ""` is refused or reported; a non-empty list
   resolves exactly as before (control); and a doc-contract test pins the Step 5(b) sentence.

### Part B — the review gate

**B1. The gate passes only on a finished review of the head.**

2. **"Review in progress" is not an answer.** CodeRabbit edits its summary to an in-progress
   state that names the head commit as the end of the range it is about to review; the re-review
   matcher accepts any non-refusal, non-acknowledgment comment of the bot written after the
   trigger, and the head check only looks for the SHA in the body, so a started review ends the
   wait as `head_sha_verified: true`. Classify the in-progress summary (and any answer while the
   bot's own check run is observed in progress) as not yet an answer, so the wait keeps polling.
   *Done when:* a fixture with the in-progress bodies observed on #1742 yields `matched: false`;
   the finished review that follows yields `matched: true` (control).

3. **A re-review awaited for one bot is not satisfied by another bot.** Reported from a consumer
   repository: `re-review --bot-kind cuioss-review-bot` matched a CodeRabbit review. Verify first;
   if confirmed, the matcher filters by the awaited bot's identity. *Done when:* a fixture with
   both bots' comments after the trigger matches only the awaited bot's; or the outline records
   the refutation with the line that already filters.

4. **A "fixed" reply waits for a green build.** Today a reply marked fixed is released once the
   stamped fix commit is the head or an ancestor of it, before verify or CI has passed on it.
   Hold it until the head that contains the fix has passed `ci-verify` (or the verify gate the
   finalize loop already records), keeping the existing `--send-unstamped-fixed` escape as the
   only bypass. *Done when:* a test shows a fixed reply held while the containing head's
   verification is pending or failed and released when it passes.

**B2. The step recovers a required bot by itself.**

5. **A stale quota notice re-triggers a required bot that has not reviewed.** The stale check
   runs before every window and trigger branch and reads the notice alone (written time plus ETA
   at or before now), so a required bot that never reviewed is settled as "nothing to do", and
   the next pass settles the same notice again until the loop-back ceiling. For a required bot
   with no review on record, a stale notice leads to a trigger (ordinary, or the escalated command
   when the bot answers "no new commit"), capped by the existing rate-window attempt counter.
   *Done when:* a test where a stale notice meets a required bot with no review yields exactly one
   trigger, and a second pass after that trigger does not trigger again within the window; a bot
   that has reviewed still settles (control).

6. **The quota wait has a margin.** The default claim window and the default
   `review_rate_window_timeout_seconds` are both 3600 s, and the wait passes no grace, so it gives
   up exactly when the claim expires; the jittered delay after expiry the spec of PLAN-LB-24 asked
   for was dropped. Give the wait a margin past expiry (the existing `poll-delay` jitter, or a
   stated grace), and make a stated reset window longer than the budget an explicit escalation
   rather than a timeout found by waiting. *Done when:* a test shows the wake instant later than
   `expires_at`, and a window longer than the budget is reported before waiting.

7. **A bot's in-place summary edit is not a new finding.** Reported from a consumer repository: a
   bot that edits its summary in place gets a second pending finding on every pre-merge re-fetch,
   which blocks the merge until resolved by hand. Verify first; if confirmed, an edit of a stored
   comment updates that finding instead of adding one. *Done when:* a re-fetch of an edited summary
   leaves one finding, with the latest body.

8. **A slow review bot is not reported as a CI timeout.** Reported from a consumer repository: the
   `CodeRabbit` commit status is in the CI-complete check set, so a rate-limited or slow bot
   surfaces as a CI timeout. Verify first; if confirmed, bot statuses leave the CI-complete set
   (they are the review gate's concern). *Done when:* a test with every CI check green and the bot
   status pending reports CI complete.

**B3. The bots' own replies are noise.**

9. **Full-review acknowledgments are not findings.** CodeRabbit answers the escalated command with
   "Action performed / Full review triggered." and edits it to "Full review finished."; the
   acknowledgment list holds "Review triggered" / "Review finished", matched as case-sensitive
   substrings, so both forms are stored as findings and are eligible answers in the re-review
   matcher. Match acknowledgments case-insensitively (or add the full-review forms) in both the
   noise filter and the matcher, and treat an edited acknowledgment as the same comment. *Done
   when:* fixtures with the bodies observed on #1742 and #1745 are dropped as noise and are not
   answers; a genuine short review is still a finding (control).

10. **The pull request is checked against a required bot's size limit before it is created.**
    Reported from a consumer repository: nothing compares the realized footprint with a required
    bot's file or line cap before `create-pr`, so an oversized pull request learns it from the
    bot. If the bot registry carries such a cap (verify first), `create-pr` reports a footprint
    over it as a warning in the step record and the PR body; it does not block. If no bot declares
    a cap, record that and drop the deliverable. *Done when:* a footprint over a configured cap is
    reported; one under it is not.

## Claim Labels

- OBSERVED (read by `pyproject_build.py` on `2fd164ec9`): `changed_paths` is split on commas and
  blank entries are dropped, so `""` gives `footprint = []` with `footprint_resolvable = True` —
  `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/pyproject_build.py:284-296`; the
  unresolvable branch's comment states why an empty footprint must not answer "a scoped run cannot
  miss a regression" (lines 288-293).
- OBSERVED (review of `370f42379`): an empty footprint yields `divergence_possible: false`; before
  PLAN-LB-33 D9 the executor stripped `""` and argparse failed — template `_drop_stray_empty_args`.
- OBSERVED (review of `370f42379`): `architecture resolve --narrow-unit ""` takes `if narrow_unit:`
  as false and returns the module-wide resolve without `bound_source` —
  `manage-architecture/scripts/_cmd_client_handlers.py` § `_narrow_resolved`.
- OBSERVED (review of `7dd1d3433`): `_match_bot_comment` (`workflow-integration-github/scripts/github_re_review.py:1460-1590`)
  accepts any non-refusal, non-acknowledgment comment after the trigger; it does not apply
  `participation_evidence_markers` or `ignore_patterns`; `_verifies_head_sha` looks for the head
  SHA in the body; the in-progress hold (`read_bot_in_progress`, lines 135-143) withholds only
  answers that do not name the head.
- HYPOTHESIS: CodeRabbit's in-progress summary names the head SHA — observed in behaviour on #1742
  (decision log 2026-10-09T23:27:21Z and 2026-10-10T09:25:01Z: matched after 34 and 35 seconds);
  no fixture holds the text. Capture it at outline from PR #1742's comments.
- OBSERVED (review of `7dd1d3433`): the stale check (`github_re_review.py:910`) runs before every
  window and trigger branch and only `attempt_held` overrides it; staleness is written time plus
  ETA at or before now (`_github_pr.py:819-834`); Branch 2 forwards `--notice-stale true` on a first
  pass without this plan's own claim (`automatic-review/SKILL.md:601, 607-626`).
- OBSERVED (review of `7dd1d3433`): `_DEFAULT_WINDOW_SECONDS = 3600`
  (`manage-locks/scripts/merge_lock.py:343`); `review_rate_window_timeout_seconds` defaults to
  3600; item 7a passes no `--grace-seconds`, so the wake is `expires_at` (`merge_lock.py:2263`);
  `phase-6-finalize/SKILL.md:1413` re-dispatches at expiry.
- OBSERVED (review of `7dd1d3433`): the fixed-reply hold releases when the stamped
  `fix_commit_sha` equals the head or is its ancestor (`_fix_commit_hold_reason`,
  `workflow-integration-github/scripts/github_pr.py:3007`); item 7c(0) stamps once the task is
  `done` and the branch `synced` (`phase-6-finalize/SKILL.md:1718-1745`); no CI or build result is
  read; GitHub only.
- OBSERVED (review of `7dd1d3433`): `is_acknowledgment_comment` (`github_re_review.py:1702`) tests
  `pattern in collapsed` (line 1734), case-sensitive; the patterns are in
  `automatic-review/standards/coderabbit.md:67-69`; the noise filter is `_is_obvious_noise`
  (`github_pr.py:494`). Observed on #1742 (findings 5d2262, 74f32d) and #1745 (46a121, dca531,
  e66a98).
- HYPOTHESIS: deliverables 3, 7, 8 and 10 come from retired lessons `2026-10-05-17-001`,
  `2026-10-05-14-006`, `2026-10-05-14-007` and `2026-10-04-09-001`, seen in consumer repositories
  and not re-checked in code — read at
  `.plan/orchestrator/lessons-routing/lessons-archive/filed-live-blockers/{id}.md`
  (verify-at-outline).
- Verify-first clause: deliverable 4 — find the record a finalize loop already keeps for "this head
  passed verification" before inventing one; if none is readable from `post_responses`, say so and
  hold until `ci-verify` is `done` at that head.
- Verify-first clause: deliverable 5 — confirm the attempt counter still caps a trigger issued from
  the stale path, so a bot that keeps refusing is escalated, not triggered in a loop.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/pyproject_build.py` — empty change list (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py` — empty narrow unit (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/execute-task/SKILL.md` — Step 5(b) (D1)
- OBSERVED: `test/plan-marshall/build-pyproject/test_pyproject_build.py`, `test/plan-marshall/manage-architecture/test_cmd_resolve_narrow_target.py`, `test/plan-marshall/execute-task/test_narrow_unit_doc_contract.py` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py` — matcher, in-progress, bot identity, stale path, acknowledgments (D2, D3, D5, D9)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` — stale notice (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — fixed-reply hold, noise filter, edited comments (D4, D7, D9)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_ci.py` — CI-complete check set (D8) (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — Branch 2 stale path, rate-window wait (D5, D6)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` — acknowledgment and in-progress bodies (D2, D9)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py` — size cap (D10) (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py` — wake margin (D6)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — item 7a wake, item 7c(0) hold (D4, D6)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/create-pr.md` — size warning (D10) (verify-at-outline)
- OBSERVED: tests under `test/plan-marshall/workflow-integration-github/` (`test_re_review_strategy_match.py`, `test_comments_stage_filters.py`, `test_comments_stage_post.py`, `test_refusal_recovery_arming_eta.py`, `test_pr_wait_for_comments_rate_limited_core.py`), `test/plan-marshall/automatic-review/`, `test/plan-marshall/manage-locks/test_merge_lock_rate_window.py`

## Dependencies and Sequencing

- Depends on: none. Launched by operator instruction beside two running plans:
  - **PLAN-LB-25** (phase and merge gates) declares `manage-locks/scripts/merge_lock.py` and
    `phase-6-finalize/SKILL.md`. Deliverables 4 and 6 touch both. Re-read both at outline, keep the
    edits to item 7a and 7c(0) narrow, and rebase onto PLAN-LB-25's landing before finalize.
  - **PLAN-LB-37** (functional review + code review) names `automatic-review/SKILL.md`,
    `automatic-review/standards/bot-participation-contract.md` and `phase-6-finalize/SKILL.md`
    among the files that mention the old self-review. This plan's edits to those files are about
    the review bots and do not touch the self-review; whichever lands second rebases.
- Suggested order inside the plan: deliverable 1 first (small, every plan's execute step depends
  on it); then 2, 4 and 9 (the wrong-green and the noise with observed fixtures); then 5 and 6;
  3, 7, 8 and 10 after their verify-first checks.
- Left out on purpose: GitLab parity for the fixed-reply hold; the Sourcery currency verdict
  (disclosed only, by PLAN-LB-24's fallback); the live-run evidence PLAN-LB-24 still owes for its
  rate-window hand-back (a Watch of this epic, not a deliverable).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-38-review-gate-and-empty-scope.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
