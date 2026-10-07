envelope_version=1
sender_type=plan
sender_id=remediate-user-facing-sites
epic=operator-ux
kind=candidate-lesson
created=2026-09-08T12:49:24Z

component=plan-marshall:automatic-review
category=improvement
created=2026-09-08
source_plan=remediate-user-facing-sites
source_signal=automated-review

# A required review bot satisfied the participation quorum on every round while filing zero findings — the barrier is correct, but nothing acts on sustained zero contribution

## What was observed

Across every review round on PR #1447 (plan `remediate-user-facing-sites`), **all 29 `pr-comment` findings were authored by `coderabbitai`**. Filtering the plan's findings store by `--author coderabbitai` returns `filtered_count: 29` against `total_count: 29` — no other reviewer identity contributed a single finding at any point in the run.

The run's review retrospective records that a second required review bot nonetheless satisfied the participation quorum on every round. This message carries the measured half (zero findings from any non-CodeRabbit author) as verified fact and the participation half as the retrospective's finding; the bot's identity is resolvable from the `automatic-review` step's `required_bots` in `marshal.json`, which was not readable from this envelope.

## This is not a defect in the barrier

The re-review barrier's contract is explicit that participation proves **participation** and nothing more — it deliberately does not claim to measure review quality, and it should not. A bot that reviews and finds nothing is behaving correctly; "no findings" is a legitimate review outcome, and a barrier that treated it as failure would punish a clean review.

So the barrier is doing exactly what it says. The observation is about what happens *around* it: nothing in the pipeline notices when a required bot's contribution is zero **round after round**, across a whole plan. The quorum is satisfied identically by a bot that reviewed thoroughly and found nothing and by one that is effectively inert, and the two are indistinguishable from any signal the run produces.

## Why the epic may care

The cost of a required bot is not zero — it is a merge-gate dependency. A required bot that never contributes still gates every merge on its participation, and the operator's own standing policy treats a stalled required reviewer as expensive enough to warrant closing and re-opening a PR rather than downgrading it. That tradeoff is only assessable if sustained zero contribution is visible somewhere.

It currently is not. Combined with the sibling candidate filed from this run — where the absence of a `rejected` route makes the measured reviewer false-positive rate read 0% instead of ~8.7% — this run produced **no trustworthy signal about reviewer value in either direction**: the bot that did contribute has its false-positive rate understated, and the bot that did not contribute is indistinguishable from one that did. The two together are why this is worth the epic's attention rather than either alone.

## What this message is not proposing

It deliberately proposes **no** change to `required_bots` membership and no automatic demotion. Whether a given bot earns a required slot is a cross-plan judgement over many runs, and one plan's evidence cannot settle it — which is exactly why this rides as a candidate for the orchestrator rather than as a lesson filed against the corpus.

## Possible directions, for the orchestrator to weigh

- Record per-bot actionable-finding counts as a run fact, so sustained zero contribution accumulates into visible cross-plan evidence instead of vanishing with each plan.
- Keep the quorum semantics exactly as they are, and surface the contribution count separately — the barrier stays a participation check, and the value question is answered by data next to it rather than by weakening the gate.
