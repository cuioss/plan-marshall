envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:37:32Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=prq-06-a-lane-override-that-cannot-take-effect-is
source_aspects=artifact_consistency,manifest_decisions,request_result_alignment

# affected_files_exact_match forwards to an aspect that has no receiving rule

## Context

`check-artifact-consistency` found a declared-versus-realized set mismatch and, instead of grading it, handed it off:

```
affected_files_exact_match,info,Set mismatch — deferred to manifest aspect
  (see check-manifest-consistency)
...
affected_files_exact_match:
  status: warn
  outline_only[4]: (none), test_ceremony_finalize_selection.py,
                   _check_routing_decisions_fixtures.py, test_check_routing_decisions.py
  references_only[2]: test_subtraction_visibility_population.py, uv.lock
  manifest_present: true
  forwarded_to_manifest: true
```

`check-manifest-consistency` then ran five checks — `manifest_version_recognized` (pass), `docs_only_diff` (skip), `early_terminate_diff` (skip), `tests_only_diff` (skip), `branch_cleanup_changes` (pass) — and emitted `findings[0]`. Not one of those five is a declared-versus-realized set comparison. **The forward lands nowhere.**

On this plan that dropped a real finding. Deliverable 6 ("Controls for the immunity rule and for the reclassified element") declared six `write-replace` files; three never shipped:

- `test/plan-marshall/manage-execution-manifest/test_ceremony_finalize_selection.py`
- `test/plan-marshall/plan-retrospective/_check_routing_decisions_fixtures.py`
- `test/plan-marshall/plan-retrospective/test_check_routing_decisions.py`

D6 therefore landed at 50% modification-intent coverage — below the 70% `fulfilled` bar — and it is the deliverable that pins the very immunity rule this plan changed. No aspect graded it above `info`.

## Root cause

A hand-off was written into one producer without a corresponding rule being added to the named receiver. The producer's own `status: warn` was downgraded to a `severity: info` finding on the strength of a forward that nothing honours — so the pipeline converted a warning into an informational note and then discarded it.

## Proposed action

Either wire up the receiver or retract the forward:

1. **Preferred** — add a `declared_vs_realized_set` rule to `check-manifest-consistency` that consumes `outline_only[]` / `references_only[]` and grades a non-empty `outline_only` at `warning` (declared-but-unshipped is a real coverage gap), leaving `references_only` at `info` (scope creep, already bounded elsewhere).
2. Failing that, stop downgrading in `check-artifact-consistency`: emit the mismatch at `warning` in place and delete the `forwarded_to_manifest` path.

Add a structural guard so a `forwarded_to_*` flag with no receiving rule fails a test rather than a plan.

## Evidence

- aspect: artifact_consistency — `affected_files_exact_match` `status: warn`, downgraded to `severity: info`, `forwarded_to_manifest: true`
- aspect: manifest_decisions — five checks, none set-comparing; `findings[0]`; `summary: passed 2, failed 0, skipped 3, findings 0`
- aspect: request_result_alignment — D6 `partial` at coverage 0.50 with the three unshipped files enumerated
