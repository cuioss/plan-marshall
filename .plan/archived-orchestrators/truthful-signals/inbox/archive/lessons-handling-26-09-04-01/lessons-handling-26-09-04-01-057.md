envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-15T13:46:51Z

component=plan-marshall:phase-6-finalize
category=bug

# pre-submission-self-review cannot converge on a consumer diff for which no surfacer has detectors

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, drain of plan
`lessons-handling-epic-residual-cleanup` (PR cuioss/TokenSheriff#744, 2026-09-15), inbox message
`lessons-handling-epic-residual-cleanup-002.md`. The orchestrator confirmed the cited log entries
exist in the archived plan before relaying.

## Observation

The diff was a Java test javadoc, two AsciiDoc files and one deleted `.log`. The only surfacer
that resolved was the plan-marshall-domain one, which has no detectors for any of those files.
The author correctly returned zero observations (`total_candidates=0` over 4 files). The verifier
then answered `may_close=no` because no real coverage occurred. Nothing changes between
iterations at an unchanged HEAD, so the documented loop can only end at the `max_iterations`
ceiling, which blocks push. The step took about 28 minutes and ended on an operator override.

Evidence: decision.log `db33b3` (11:10:13Z) candidate-count gate total_candidates=0;
`24dc3b` (11:11:08Z) "may_close=no — all 4 files are class 'other' with zero detectors, so no real
coverage occurred"; `ef7f20` (11:38:42Z, WARNING) "OPERATOR OVERRIDE … a re-fire at unchanged HEAD
is guaranteed to reproduce the same answer … This is NOT a converged close."

## Why it matters

The verifier is right that nothing was reviewed. The loop is wrong to treat that as something
another iteration could fix. The result is a gate that blocks push, can only be forced, and
records the forced close with a warning rather than a structured "not covered" verdict.
Downstream, PR #744's only review was the PR bots, and nothing in the landing facts says so in a
machine-readable way (`step.pre-submission-self-review.may_close=no` is the only trace).

## Candidate direction

When no surfacer resolves detectors for any file in the diff, end the step deterministically with
an explicit `not_covered` / `no_applicable_detectors` outcome: non-blocking, recorded as a coverage
gap, and carried into the landing facts. Do not enter a loop whose verifier answer cannot change.
Related: `-010` (self-review candidate classes). This relay is about the empty-detector case, not
candidate quality.
