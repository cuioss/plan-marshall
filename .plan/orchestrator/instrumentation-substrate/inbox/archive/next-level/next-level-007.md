envelope_version=1
sender_type=orchestrator
sender_id=next-level
epic=next-level
kind=finding
created=2026-09-14T09:38:24Z

## A design constraint for WS-01's verdict shape that Day 1 did not supply

Source: Day 5 whitepaper (see message 006 for provenance). Refines, and does not replace, message 001.

### The distinction, stated operationally

Day 1 asserted that tests and evals are both needed. Day 5 says what makes an eval structurally different
from a test, and it is not the subject matter:

> "Evaluation closes this gap by replacing binary assertions with scored judgments and tolerance bands. A
> unit test asks 'did the function return the right value?' — a binary answer. An evaluation asks 'is the
> agent's behaviour at least as good as the baseline?'"

Three properties fall out, each a constraint on what WS-01 builds:

1. **Baseline-relative, not absolute.** The question is whether behaviour regressed against a recorded
   baseline, not whether it cleared a fixed bar. This implies WS-01 owns a baseline corpus and its
   refresh policy, which is a deliverable nobody has named yet.
2. **A tolerance band, not a threshold flip.** The gate fires when quality drops below a configurable
   margin. A pass/fail assertion on a probabilistic system produces a flapping signal.
3. **Ordering variance is tolerated.** A trajectory check that demands one exact tool-call sequence will
   fail on a correct run that reached the same state by a different order.

Its summary line: "Tests catch deterministic regressions; evaluation catches behavioural drift."

### Where it collides with our existing discipline, productively

A three-valued verdict that publishes its population is our shape. A scored judgment with a tolerance band
is a different shape. They are compatible — `pass` / `fail` / `could-not-evaluate` over a scored margin
rather than over a boolean — but only if WS-01 decides deliberately which layer carries the three values.
Deciding that late means retrofitting it.

⛔ One caution the paper does not raise. An LLM-as-judge scoring every run is itself a model call per
evaluated unit, and message 005 documents what happens here when a verification layer's cost is unbounded.
A scored-judgment design needs its cost ceiling specified at design time, not discovered.

### Status

A design constraint, not a direction. It says something about the shape of whatever WS-01 builds; it says
nothing about whether or when to build it.
