envelope_version=1
sender_type=plan
sender_id=fail-closed-signal-integrity
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T21:10:12Z

component=project:finalize-step-review-retrospective
category=bug
bundle=plan-marshall

# review-retrospective cannot distinguish a REFUSED reviewer from a clean one

The review-retrospective artifact represents a reviewer that produced no comments and a
reviewer that never ran the same way: **by having no row**. There is no representation for
"this reviewer was enabled, was invoked, and refused".

Observed live on PR #1081: `sourcery` refused with `hard_quota` on **all three** review
rounds and simply has no row in the artifact. A reader of the artifact sees two clean
reviewers and concludes the diff was reviewed by two bots — it was reviewed by two, refused
by a third, and the artifact cannot say so.

This is a fail-open *inside the review apparatus itself*, which is the surface the epic uses
as evidence that a review happened.

## Impact

Every consumer of the artifact — the finalize summary, the epic's landing analysis, any
later audit of "did the bots see this diff" — reads an absent row as "nothing to report"
when it can equally mean "could not report". This is the exact archetype the epic exists to
kill, sitting in the tool that measures reviews.

Reinforces the standing rule that a green finalize is never proof the bots saw the diff, and
that only per-reviewer participation evidence settles it.

## Solution

Emit a row per *enabled* reviewer, not per *responding* reviewer, and give the row an
explicit participation state:

- `reviewed` — ran and produced comments (including zero actionable ones).
- `refused` — ran and declined, carrying the refusal reason (`hard_quota`, rate limit, etc.).
- `absent` — enabled but never observed at all.

The enabled-reviewer set is the population the rows must be derived from; deriving rows from
the responding set makes the detector's population a strict subset of its own domain — the
recurring population-derivation defect.
