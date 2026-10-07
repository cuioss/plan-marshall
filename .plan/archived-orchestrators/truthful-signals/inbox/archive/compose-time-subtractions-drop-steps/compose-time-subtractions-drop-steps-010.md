envelope_version=1
sender_type=plan
sender_id=compose-time-subtractions-drop-steps
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T12:42:11Z

## Proposed lesson metadata

- `component`: `plan-marshall:phase-6-finalize`
- `category`: `bug`
- `title`: A refusing review bot's check turned green and was counted in the 11/11 merge gate

## Observation

PR #1066 recorded **both** of these, in the same run, about the same bot:

- `ci-verify` step outcome (status.metadata.phase_steps):
  `"CI green at 5a4ab1a8 (CodeRabbit check pending = rate-limit refusal, not a signal)"`
- `branch-cleanup` work-log line at 12:04:23Z:
  `"PR 1066 is green (11/11 checks pass incl CodeRabbit) and enqueued to the GitHub merge queue"`

The review-retrospective, written between those two points, is unambiguous:

> **CodeRabbit (`coderabbitai`) and Sourcery (`sourcery-ai`) posted zero
> findings** — neither reviewed this PR.

So the sequence was: CodeRabbit refused → the refusal was correctly identified
and correctly discounted at `ci-verify` → CodeRabbit's **check** later resolved
green → and the **merge decision** counted that green check as one of the 11
passing checks, explicitly naming it.

## Why this is distinct from the queued message 006

Queued candidate-lesson 006 asks for awaitable-vs-terminal refusal
classification so a recoverable refusal gets waited out. That is about
*recovering* the lost review.

This is a different defect on the other side of the same event: even with
`review_rate_window_await` left off, the run had already **correctly identified**
the refusal and written it down. That correct reading was then **overwritten** by
the bot's own check state at the point where it mattered most — the merge gate.
The merge gate cannot distinguish:

- check green because the bot reviewed and found nothing, from
- check green because the bot gave up.

Both render identically in the `N/N checks pass` aggregate, and the aggregate is
what licenses the merge.

## Why it belongs to this epic

The corpus already carries *"check states lie in both directions"* and *"only
`ci pr comments --pr-number N` is evidence of participation"*. The new
contribution is that **the run knew**. This was not a missed signal — the refusal
was detected, named, and recorded as "not a signal", and then the merge gate
re-credited it 43 minutes later from a different source. A confident aggregate
displaced a correct disaggregated reading that already existed on disk.

## Owed work

1. The pre-merge check aggregate must not count a check owned by a bot the run
   has already recorded as refused. The refusal record exists in
   `phase_steps["6-finalize"]["ci-verify"]` at the moment `branch-cleanup` runs —
   it needs only to be consulted.
2. The merge-gate display detail must carry the participation count, not just the
   check count: `11/11 checks pass, 1/3 reviewers participated` is the line that
   would have made this visible at the moment of the merge decision.
3. Generalise: any gate that aggregates per-producer states must subtract
   producers the run has recorded as non-participating, rather than reading their
   terminal state as agreement.
