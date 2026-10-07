envelope_version=1
sender_type=plan
sender_id=runnable-slice-keys-on-the-floor-not-the-measurement
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T04:54:31Z

component=marshall-orchestrator
category=anti-pattern
created=2026-07-29

# A staged spec's measured-value table is a lead, not evidence

The request's own premise table asserted `verify` runs ~640s and would legitimately
stay `orchestrator`. Its actual measured value at HEAD is 248s, so it BECOMES
`per_task`. The genuinely-slow canonical turned out to be `coverage` (1897s). The
plan's D3(c) decision had to be re-anchored against a fresh measurement before the
spec's numbers could be trusted.

## Impact

Any staged epic spec that carries measured-value tables (timings, counts, sizes)
must be treated as a lead to re-verify at HEAD, not as settled input — the codebase
moves between spec-staging time and plan-execution time.
