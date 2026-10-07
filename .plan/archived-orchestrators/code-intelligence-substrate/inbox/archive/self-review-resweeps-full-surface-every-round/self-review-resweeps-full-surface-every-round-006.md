envelope_version=1
sender_type=plan
sender_id=self-review-resweeps-full-surface-every-round
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-09T03:22:43Z

component=plan-marshall:phase-6-finalize
category=bug
bundle=plan-marshall
confidence=high
source_plan=self-review-resweeps-full-surface-every-round
source_aspects=invariant-summary,artifact-consistency

# 19 pending qgate findings reached merge because no 6-finalize handshake row was ever captured

PR #1126 merged with **19 Q-Gate findings still at `resolution: pending`** — every finding the six `pre-submission-self-review` rounds filed. The blocking gate that exists to prevent exactly this never evaluated them.

The mechanism, read off `_invariants.py`:

- `_ACTIONABLE_FINDING_TYPES` **includes `qgate`**, aggregated across every `QGATE_PHASES` phase at `--resolution pending`.
- `_BLOCKING_BOUNDARIES` is **exactly `frozenset({'6-finalize'})`** — the exception only raises when the capture's `phase` argument is `6-finalize`.
- The plan's `handshakes.toon` carries rows for `1-init`, `2-refine`, `3-outline`, `4-plan`, `5-execute` and **none for `6-finalize`**.

No `capture --phase 6-finalize` was persisted, so the one boundary where a pending `qgate` finding blocks was never reached. The class docstring claims the intra-finalize boundaries (`automated-review → branch-cleanup`) are "guarded by the phase-6-finalize orchestrator re-issuing `phase_handshake capture --phase 6-finalize`"; this run's handshake store does not corroborate that.

## Root cause

The gate's arming condition is a *call that must happen* rather than a *state that must hold*. A missing call is indistinguishable from a passing gate: both leave no row and raise nothing.

## Solution

Two candidate directions, both worth weighing:

- Make the absence of a `6-finalize` handshake row a **blocking condition at the merge boundary**, so "the gate never ran" cannot present as "the gate passed".
- Have the self-review loop-back path **resolve** its Q-Gate findings when it lands their fixes, so the store reflects reality rather than accumulating 19 permanent `pending` rows on a green plan.

Both are needed: the first closes the gate, the second stops the gate from having to be closed against a store that is wrong anyway.

## Impact

**No real defect shipped here** — the 19 findings were genuinely fixed; only their records stayed `pending`. That is exactly what makes it worth filing: the gate's inertness was invisible precisely because the outcome was fine. On a run where the fixes had NOT landed, the same silence would have shipped them.

`pending_findings_blocking_count` is therefore not a trustworthy merge signal on this path. Anything that reads it as one — including a retrospective audit counting "plans that merged clean" — is reading a number nobody computed.
