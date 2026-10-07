envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:00:21Z

component=plan-marshall:phase-3-outline
category=improvement
bundle=plan-marshall

# A deliverable that declares settled inputs before its own gate runs must route request divergence to an explicit decision

The clarified request asked to "pin orchestrator.effort to an explicit opus-tier
level". Deliverable 5 pinned `analyze` and `decompose` to `level-5`, which the
effort-levels table confirms is (opus, high) — correct. It pinned `reader` to
`level-3`, which the same table confirms is (sonnet, high) — NOT the opus tier.

The divergence was disclosed and reasoned, not silent: the outline recorded that
the reader performs bounded extraction from already-fetched text rather than
judgement, and that the point of the pin is that the level is STATED rather than
inherited. The request also delegated the reader surface to deliverable 0's
finding. What made it worth recording is that the request's headline wording is
unqualified, and that deliverable 5 declared all three levels as settled inputs
BEFORE its own gate (deliverable 1) ran.

Source record: Q-Gate finding `3933d4`, phase `3-outline`, resolution
`taken_into_account`.

## Solution

When a deliverable declares values as settled inputs ahead of the gate that would
validate them, any divergence from the request's headline wording must be routed
to an explicit operator decision rather than carried on the outline's own
reasoning. Here that happened: decision-log entry `dabd0d` bakes in the operator's
answer (analyze=level-5, decompose=level-5, reader=level-3, explicit rather than
inherited), and entry `5d1d6a` records the same reader-surface default applied with
none flagged as blocking.

## Impact

The generalizable rule is the routing obligation, not the specific tier. A
disclosed divergence is still a divergence until an operator decision settles it;
the outline's own rationale cannot close it.
