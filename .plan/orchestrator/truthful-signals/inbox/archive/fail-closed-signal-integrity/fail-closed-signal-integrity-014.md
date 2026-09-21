envelope_version=1
sender_type=plan
sender_id=fail-closed-signal-integrity
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T22:08:14Z

component=plan-marshall:phase-6-finalize
category=improvement
bundle=plan-marshall

# Five self-review passes cost 709K tokens and still missed what one free reviewer found

This is a cost-calibration message, not an argument against self-review. The step earned its keep
on defect count; it did not earn it on the defect that mattered most, and its price needs to be
visible when the step is configured.

## The measured numbers, from this plan's own records

- `decision.log` `64b2a4`: `Recorded pre-submission-self-review phase=6-finalize
  outcome=executed — total_tokens=709472, tool_uses=169, duration_ms=2342530`.
- That is **13% of the plan's entire ~5.47M-token spend** on one finalize step, and 39 minutes of
  recorded agent time spread across 5 passes and ~2h of wall time (13:59 → 15:52, plus a re-fire
  at 19:00).
- 10 defects found. **2 of the 10 were introduced by a prior pass of itself** (see inbox 006). Net
  external yield: 8 defects for 709K tokens ≈ **89K tokens per externally-caused defect**.
- One of the 5 passes (pass 4, the convergence check) was killed by a harness stream stall at
  15:00:24Z and had to be re-run, so part of the spend bought nothing.

## What it did not catch

Clause (d) of `error-handling.md` — text this plan authored, in the plan's own central deliverable
— contains a GOOD example that demonstrates the anti-pattern the clause forbids, and that example
had *already been used* to justify retiring lesson `2026-07-11-15-001` (see the sibling
candidate-lesson on retirement evidence). Five passes over that file did not flag it. CodeRabbit
flagged it in one pass, at zero token cost, once the PR was open.

The same pass also missed clause (f)'s comment misnaming its own mechanism.

## The honest read

Self-review's yield here was concentrated in structural/mechanical classes (the kind the
`ext-self-review-plan-marshall` candidate detectors surface deterministically). The one defect
class it demonstrably did not reach was **semantic self-contradiction inside prose the same run
had just authored** — which is precisely the class an independent reader is good at and an author
re-reading their own text is bad at, however many times they re-read it.

## Solution

1. **Publish the price.** Surface the step's recorded token cost in its `display_detail` so the
   709K is visible at the point the lane is configured, not only in a retrospective.
2. **State the non-coverage.** The step should declare what it is *not* expected to catch. A
   `5 passes, 10 defects found and fixed, converged` display detail reads as a coverage claim; it
   is a volume claim. (Recurrence of the volume-read-as-coverage archetype.)
3. **Calibrate the stopping rule against marginal yield, not against convergence alone.** Passes
   1-3 each found defects; pass 4 converged; pass 5 (a re-fire after loop-back) found 1. Consider
   whether passes beyond the first two should be scoped to *newly changed* text rather than
   re-sweeping the whole footprint.
4. **Do not spend the budget where an external reviewer is already free.** The PR review is going
   to run regardless. Self-review's comparative advantage is catching what blocks the PR from
   being *worth* opening, not duplicating what CodeRabbit does better.
