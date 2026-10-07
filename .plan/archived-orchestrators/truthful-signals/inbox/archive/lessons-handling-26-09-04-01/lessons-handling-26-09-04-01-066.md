envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-16T15:33:08Z

component=plan-marshall:manage-references
category=improvement

# Confirm-and-close: `references.affected_files` under-recorded a landing's realized footprint (observed 2026-09-08; the current surface looks to have superseded it)

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01` on 2026-09-16. **This is a
verify-and-close request, not a new defect report.** It is filed because the observation sat in the
epic ledger unrelayed until close, and closing it silently would leave no record that it was checked.

## What was observed, and when

While reconciling PLAN-11 (Token-Sheriff PR #718, 2026-09-08), the orchestrator recorded:

> `references.json.affected_files` under-records the realized footprint. It lists 5 files; the merge
> commit touches 7 — `RefreshAdversarialTest.java` and `RefreshTestSupport.java` (both landed in the
> TASK-9/TASK-10 review-fix round) are missing. A reconciliation trusting the realized side alone
> would have missed the two files carrying the negative controls.

The consequence recorded at the time: **both sides of the declared-vs-realized comparison were
incomplete on that plan**, so a reconciliation had no trustworthy realized side to compare against.

## Why it looks already superseded

Read at plan-marshall HEAD on 2026-09-16, `manage-references` now separates the two:

- `affected_files` is documented as *"the MUTATION half of the plan's declared footprint … Contrast
  `realized_footprint`, which records what the worktree actually touched."*
- `_cmd_compute_footprint.py` `cmd_capture_footprint` derives the live footprint from worktree git state
  and writes `references.realized_footprint`.
- `_cmd_reconcile_scope.py` names the realized footprint as side C of a three-way reconciliation.

On that reading the 2026-09-08 observation is a complaint about the wrong key: `affected_files` was never
meant to be the realized footprint, and the realized side now has a derived key of its own.

## The ask

Confirm one of two things, so this can be closed on a fact rather than on my reading:

1. **Superseded** — the derived `realized_footprint` closes it, and a review-fix round landing files
   after the initial derivation is now reflected because the capture runs at finalize. Then nothing is owed.
2. **Still live in part** — if `realized_footprint` is captured once at a point a later review-fix round
   can still move the tree, the same under-recording survives under a new key, and the capture point is
   what needs fixing rather than the key.

The discriminator is the same one that made the original observation matter: files added in a **review-fix
round after the main implementation** are precisely the ones an early capture misses.
