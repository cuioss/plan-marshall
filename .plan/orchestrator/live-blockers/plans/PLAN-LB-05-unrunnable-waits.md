# PLAN-LB-05: Wait procedures the harness cannot run

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-05-unrunnable-waits.md` and is queued as one row file,
> `queue/PLAN-LB-05.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Three finalize waits tell the agent to pace a poll with a standalone foreground `sleep`, which the
harness refuses, so the wait's budget is unreachable: the review-bot completion poll ended after a few
unpaced reads and the step was marked done while the bot was still reviewing; the merge-lock admission
wait and the merge-queue landing wait have the same shape. Two further waits mislead rather than block:
documents disagree on whether an orchestrator-tier build may run in the background, and a CI wait that
lapses while every check is still running is filed as a `ci_timeout` finding and costs a triage round.
This plan moves each short pacing wait into the script that owns the query (a bounded, script-side wait
the caller re-issues), states one runnable rule for long builds, and classifies a lapsed wait on a live
run as "still pending". Carries forward process-compliance PLAN-23 deliverable D4 (D4a, D4b) and the
remedy direction of truthful-signals PLAN-TRUTH-169 (folded recurrences) and PLAN-TRUTH-162 (D3, second
member).

## Deliverables

1. **The merge-lock admission wait runs without `sleep`.** `branch-cleanup.md` prescribes "a SINGLE
   standalone `sleep {interval}` Bash call" between `merge_lock acquire` polls in both admission loops
   (the early-hold reference and the Pre-Merge Gate loop). Give the wait a script-side form: one call
   that keeps trying for admission for up to a caller-supplied number of seconds (for example
   `--wait-seconds`), returns the same `admission` discriminator as today plus the seconds it waited,
   and is bounded below the harness per-call ceiling so the caller re-issues it until
   `merge_queue_wait_budget_seconds` is spent. The wait must sit between non-waiting acquire attempts,
   never inside the store's read-modify-write section (see the verify-first clause on
   `merge_lock.py`). Rewrite both loops onto it. Done when: a test shows the call returning
   `admitted` as soon as the front holder releases, and returning the blocked discriminator with the
   waited time when the bound lapses; and no `sleep` instruction remains in the two admission loops.
2. **The merge-queue landing wait runs without `sleep`.** `branch-cleanup.md` § "Landing poll loop"
   paces `ci pr view` reads with a standalone `sleep`. A bounded wait for exactly this condition
   already exists and is unused here: `ci pr wait-for-queue-settle --pr-number N --timeout S
   --interval I`, returning `settle` of `merged` / `closed` / `dequeued` / `timeout`. Rewrite the
   landing loop to re-issue that verb with a `--timeout` below the per-call ceiling until
   `{wait_budget}` is spent, mapping `merged` to the landed branch, `closed` and `dequeued` to the
   Landing-gate failure path, `timeout` with budget left to another call, and an `error` to the
   failure path as today. Keep the `--pr-number` selector and the `merge_hold_budget_seconds` bound.
   Done when: a doc test asserts the landing loop names the wait verb and contains no `sleep`
   instruction, and the four `settle` values each have exactly one documented branch.
3. **The review-bot completion poll runs without `sleep`, and says what it saw.** `automatic-review`
   § "Completion-aware poll" paces `bot_completion` reads with `sleep 30`. Add a bounded wait to the
   `bot_completion` verb (for example `--wait-seconds` with an interval): it polls the bot's check-run
   until it completes or the bound lapses, and returns the existing `{status, in_progress, completed}`
   fields plus `timed_out` and the seconds waited; `no_check_name` and `unconfigured` return at once.
   The workflow re-issues the call until `review_completion_poll_timeout_seconds` is spent. When a
   bot is still in progress at that bound, the step records it in its `display_detail` and step
   record, not only in a WARNING log line. Done when: a test with a check-run that flips to completed
   on the third read returns `completed: true` from one call; a test with a check-run that never
   completes returns `in_progress: true, timed_out: true` after the bound; and the poll section holds
   no `sleep` instruction.
4. **One rule for long builds, and it can be followed.** `await-long-running.md` and
   `build-server-client/SKILL.md` forbid backgrounding or sleeping a build wait; `execution.md`
   § "Orchestrator-tier phase-5 verification", `ref-workflow-architecture/standards/agents.md` and
   `phase-5-execute/standards/canonical_verify.md` say the await-long-running seam is the only
   component that backgrounds a build and tell the orchestrator to use `run_in_background: true`.
   Meanwhile the build wrapper's daemon route re-issues `wait` in an unbounded in-process loop, so a
   foreground wrapper call for a build longer than the per-call ceiling cannot return in time
   whichever document is obeyed. Pick one rule and make all five documents state it: the wrapper call
   for a daemon-routed build returns within a bound below the ceiling, either with a terminal result
   or with a live `running` status and the job id, and the orchestrator re-attaches with the
   documented bounded `wait`; backgrounding is named only for the non-daemon fallback, if it is kept
   at all. Done when: a test drives the routed path with a job that outlives the bound and receives
   the `running` hand-back instead of blocking; a doc test asserts none of the five documents
   prescribes `run_in_background` for a daemon-routed build while another forbids it.
5. **A wait lapse on a live CI run is "pending", not a finding.** In `consume-failures` mode the
   precondition returns `wait_failed` / `ci_final_status: timeout` when its clamped wait ends, and
   `ci_verify.py` then retains every still-running check and classifies it `ci_timeout`
   (`wait_outcome == deadline_exceeded` routes any check without a definitive conclusion to the
   timeout row). On a repository whose verify job outlasts the clamped wait this files findings on
   every first read and spends a loop-back round on a run nothing has failed in. Change the
   classification: a check that is pending, queued or in progress when the wait deadline passes
   produces no finding; the executor returns a distinct pending outcome and the dispatcher re-issues
   the precondition, up to a documented bound of re-waits, before anything is filed. `ci_timeout`
   stays for a check whose own conclusion is `timed_out`, and for a run still not terminal after the
   re-wait bound. Done when: a test feeding `deadline_exceeded` with only in-progress checks gets
   zero findings and the pending outcome; a test with a `timed_out` conclusion still gets one
   `ci_timeout` finding; a test past the re-wait bound gets the finding; and `ci-verify.md` row (h)
   and the precondition table in `phase-6-finalize/SKILL.md` describe the same behaviour.

## Claim Labels

- OBSERVED: the harness refuses a standalone foreground `sleep`; the documented `sleep 30` in the completion poll was refused on PR #1704 and the step was marked done with the bot still in progress — lesson `2026-10-07-07-007` (read through `manage-lessons get`), and the corpus's own rule at `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/tool-usage-patterns.md` § "No sleep for external waits", which forbids `sleep N` for external waits and says to extend the CI abstraction with a `wait-for-*` verb instead
- OBSERVED: the merge-lock admission loops prescribe a standalone `sleep {interval}` between `acquire` polls — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:373`, `:579`, `:594`, `:601`, `:608`
- OBSERVED: `merge_lock acquire` takes `--plan-id`, a no-op `--timeout` and `--no-title-token`, and has no waiting form — `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py:2295-2317`
- OBSERVED: `merge_lock.py` declares "This module has no `time.sleep` and must keep none", reasoning that a wait inside a primitive every finalizing plan contends on would hold a process open — `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py:114-123`
- OBSERVED: the landing loop paces `ci pr view` with a standalone `sleep {interval}` — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:1572`, `:1590`
- OBSERVED: a bounded landing wait exists and `branch-cleanup.md` does not use it — `cmd_pr_wait_for_queue_settle` at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py:2857`, documented at `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/leaf-command-reference.md:46`; its only workflow caller is `plan-orchestrator/workflow/land.md:187`
- OBSERVED: `pr wait-for-queue-settle` does not report `dequeued` for a PR ejected before the wait began; it runs to `timeout`, and `pr queue-state` is the single-read verb for that case — docstring of `cmd_pr_wait_for_queue_settle`, `_github_pr.py:2871-2891`
- OBSERVED: the completion poll prescribes `sleep {interval}` / `sleep 30` between `bot_completion` reads, and at the bound only logs a WARNING — `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:345`, `:351`, `:352-360`
- OBSERVED: `bot_completion` is a single read with no waiting form — `cmd_bot_completion` at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py:2430-2524`
- OBSERVED: the build-wait documents contradict each other — "The build consumer does NOT use this detach-and-notify seam" and "Do NOT `run_in_background` or `sleep` the daemon `wait`" at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/await-long-running.md:13`, `:28` and `marketplace/bundles/plan-marshall/skills/build-server-client/SKILL.md:31`, against "background (`run_in_background: true`)" and "the orchestrator's `await-long-running` seam always does" at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md:370-373`, `:386`, `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/agents.md:170-172` and `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/canonical_verify.md:86`
- OBSERVED: the wrapper's daemon route re-issues `wait` in `while True` until the job is no longer `running`, with no bound on the wrapper call itself — `_route_to_daemon` at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py:788-796`; the client-side `wait` verb is bounded (`--bound`, default 300 s) per `build-server-client/SKILL.md:56-68`, `:189-193`
- HYPOTHESIS: orchestrator-tier builds in this repository resolve to budgets above the 600 s per-call ceiling (745–3095 s reported), so the foreground wrapper call is backgrounded by the harness whatever the documents say — confirm/refute with `architecture resolve --command verify` and `module-tests` in the plan's worktree, reading `bash_timeout_seconds` (verify-at-outline)
- OBSERVED: the ci-arm precondition returns `wait_failed` / `ci_final_status: timeout` / `wait_outcome: deadline_exceeded` when the clamped wait ends, while only the per-signal arms map the same condition to `arm_pending` — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_complete_precondition.py:741-787`, `:864-876`
- OBSERVED: `ci_verify.py` retains pending checks under `deadline_exceeded` and classifies any check without a definitive conclusion as `ci_timeout` — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_verify.py:193-194`, `:731-751`; the documented contract says the same at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md:189`, `:195-203` and `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:503`, `:505`
- HYPOTHESIS: the clamped wait is about 569 s against a verify job of about 25 minutes in this repository, so the first reads of a normal run always lapse — confirm/refute at `ci_complete_precondition.py` § `_clamp_wait_ceiling` and `_MAX_INNER_WAIT_SECONDS` plus the recorded duration of recent `verify` runs (verify-at-outline)
- HYPOTHESIS: no other finalize or execute document prescribes a standalone `sleep` outside the rate-window recovery owned by PLAN-LB-18 — confirm/refute with a content search for `sleep` across `marketplace/bundles/plan-marshall/skills/**/*.md` and `.claude/skills/**`, classifying each hit (verify-at-outline)
- Verify-first clause: settle where the merge-lock wait lives before scoping deliverable 1. The module's no-sleep rule is stated for the rate-window claim and the read-modify-write section; the plan must either place the pacing between whole non-waiting `acquire` attempts and amend that paragraph to say so, or put the wait in a separate verb or script. A wait that holds the store lock while sleeping is not acceptable.
- Verify-first clause: for deliverable 4, establish what a re-attached `wait` returns compared with the wrapper's own result (result TOON, findings persistence, the `kind=build` ledger stamp the freshness gate reads). If the hand-back cannot carry those, the plan narrows deliverable 4 to making the five documents agree on the rule that is actually runnable today and records the script change as owed.
- Verify-first clause: for deliverable 5, read how the dispatcher consumes `consume-failures` at `phase-6-finalize/SKILL.md` § "Precondition resolution" and decide whether the re-wait is driven by the precondition (returning a pending status the dispatcher loops on) or by the executor; one owner only.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — admission loops and landing loop (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py` — bounded admission wait and the no-sleep paragraph (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/SKILL.md` — `merge_lock acquire` canonical invocation (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — § "Completion-aware poll" only (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — `cmd_bot_completion` and its argparse entry (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md` — `bot_completion` canonical invocation (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/await-long-running.md` — build-consumer rule (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — § "Orchestrator-tier phase-5 verification" (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/agents.md` — § "Leaf cannot reap a backgrounded build" (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/canonical_verify.md` — `execution_tier=orchestrator` bullet (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-server-client/SKILL.md` — wait rule and re-attach contract (D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py` — `_route_to_daemon` bounded hand-back, only if the verify-first clause on deliverable 4 allows the script change (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_verify.py` — `classify_check` and the failing-check filter (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_complete_precondition.py` — ci-arm lapse resolution (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md` — taxonomy row (h) and its note (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — § "Precondition resolution" table only (D5)
- OBSERVED: `test/plan-marshall/manage-locks/test_manage_locks_merge_lock_cli.py` — admission-wait tests (D1)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_pr_bot_completion.py` — bounded-wait tests (D3)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_ci_verify_core.py` — pending-versus-timeout classification (D5)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_ci_complete_precondition_checks.py` — lapse resolution (D5)
- HYPOTHESIS: `test/plan-marshall/script-shared/test_build_execute_factory.py` — routed hand-back test, same condition as the factory entry (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/test_no_standalone_sleep_in_wait_docs.py` — new doc test for D1–D4 wording (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-LB-18 (`automatic-review/SKILL.md`, `manage-locks/SKILL.md`, `merge_lock.py`). Scope boundary: the CodeRabbit rate-window wait — the up-to-an-hour quota wait in `automatic-review/SKILL.md` § "Rate-limit refusal recovery", its Branch 3 poll, the `poll-delay` jitter sleep and the `rate-window` verbs — belongs to PLAN-LB-18. This plan owns the short pacing sleeps (admission, landing, completion poll) and the timeout classification, and must not edit the recovery section. Sequence the two; do not run them together.
- Overlaps with: PLAN-LB-09 (`branch-cleanup.md`, pre-merge check), PLAN-LB-10 (`ci_verify.py`), PLAN-LB-06 (`execution.md`), PLAN-LB-12 (`script-shared/scripts/build/*`), PLAN-LB-19 (`github_pr.py`), PLAN-LB-02 and PLAN-LB-11 (`phase-6-finalize/SKILL.md`). Each touches a different section; sequence rather than pair.
- Adjacent to: the landing gate's inability to tell an ejected PR from a queued one. `pr wait-for-queue-settle` runs to `timeout` for a PR ejected before the wait began; this plan keeps the existing budget-exhaustion path for that case and does not add the `pr queue-state` pre-read.
- Adjacent to: the lesson's third proposal, a pre-merge barrier that refuses a merge while a required bot is still in progress for the candidate commit. That is review-gate currency (PLAN-LB-19) and is left out on purpose; deliverable 3 only makes the poll runnable and its outcome visible.
- Left out on purpose: reaping the build when a daemon wait times out, per-test time budgets, and the adaptive build budget (truthful-signals PLAN-TRUTH-169 D1–D4; the build half is PLAN-LB-12's subject); the argparse-hint and documented-invocation deliverables of PLAN-TRUTH-162 (D0–D2, D4).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-05-unrunnable-waits.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
