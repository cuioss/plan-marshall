envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:51:27Z

component=plan-marshall:phase-2-refine
category=improvement

# An all-dimensions-100% confidence score needs evidence, not a bare accept

Source: Q-Gate finding 039658 (2-refine, resolution=accepted).

All six confidence dimensions scored 100, which the mechanical Q-Gate check flags as
suspicious by default. The accept was justified here — the request was an
orchestrator-authored, previously-audited spec carrying explicit
OBSERVED/HYPOTHESIS/REFUTED/UNVERIFIABLE per-claim labels, falsifiable Done-when
criteria, and 6/6 load-bearing claims plus 3/3 proposed fixes spot-checked against
HEAD during refine steps 3b/3c.

## Solution

When the suspicious-perfect-score check fires, the accept must cite the independent
verification that was actually run (which claims, how many, against what HEAD), not
merely assert that the source was pre-audited. A bare "previously audited" accept is
indistinguishable from a rubber stamp.

## Impact

Applies to every refine run over an orchestrator-authored spec, which is the normal
shape for an orchestrated plan.
