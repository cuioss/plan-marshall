envelope_version=1
sender_type=plan
sender_id=lb-23-verify-builds
epic=live-blockers
kind=candidate-lesson
created=2026-10-09T10:01:45Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-10-09
bundle=plan-marshall
source_plan=lb-23-verify-builds
confidence=high

# Bound self-review rounds whose fixes keep seeding new doc-claim findings

## Context

On plan lb-23-verify-builds (PR 1729) the pre-submission self-review ran five rounds and returned 6, 7, 4, 5 and 10 findings (32 in total, all fixed). It never produced a clean round. It was closed by operator decision ("close the review and ship") and then re-closed by the orchestrator after each later commit without being re-run. The five reviewer dispatches alone cost 2,159,266 tokens by their dispatch-boundary rows, before the five fix dispatches; finalize as a whole recorded 7,235,372 dispatched tokens, 58 percent of the plan.

## Root cause

Each fix commit rewrote prose and docstrings, and the next round audited exactly that new prose. Of the 32 findings, 25 were `contract_drift` doc-claim findings; round 3 was classified self-seeding by its own reviewer (all 4 findings sat in sentences the round-2 fix had rewritten). The reviewer also widened its reading each round (contract sources never read in full in any round), so later rounds reached pre-existing prose the plan had only made false, and a round-5 sweep of `_freshness_crosscheck.py` produced 6 findings in one file. Nothing in the loop distinguishes "the delta is converging" from "the audited surface keeps growing".

The loop still earned its place: round 4 found a shipped-code defect (the supervisor waited on the job leader, returned in 0.00 s and left a SIGTERM-ignoring build alive) and round 5 found a second (PermissionError escaping `_stop_job_tree` and recording a timed-out job as `failure`).

## Proposed action

- Separate behavioural findings from doc-claim findings in the loop decision: loop on behavioural ones; batch doc-claim ones into a single deletion-first fix and do not re-audit prose written by a fix commit as a new round.
- Require the class sweep before the fix, not after: when a round reports a `contract_drift` cohort, the fix dispatch sweeps every sibling statement of the same claim in one pass (rounds 2 to 5 each re-found siblings of an earlier class).
- Check whether main commit d8b0284ef (PR 1726, "grade findings by severity and loop only on blocking ones"), which landed while this plan was in finalize, already covers this; if it does, this is a recurrence record for it rather than a new lesson.

## Evidence

- aspect: plan_efficiency - five returned_with_findings rows for the reviewer: 460,998 / 322,581 / 363,286 / 549,259 / 463,142 tokens.
- aspect: chat_history_analysis - round reports: "self-review found 6 / 7 / 4 / 5 / 10 issues"; round 3: "By the workflow's definition the round is self-seeding".
- status record: `pre-submission-self-review` firing_count 8, prior firings loop_back x5 then done x2, final facts `may_close: operator_override`.
- work log: "Loop-back iteration 5/5 (pre-submission-self-review, target=6-finalize) - last iteration the ceiling admits".
