envelope_version=1
sender_type=plan
sender_id=crashed-participation-gate-records-a-pass
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T19:36:17Z

# Re-derive check-routing-decisions removal-cause regexes against the live lane_resolution emitter

component: plan-marshall:plan-retrospective
category: bug
confidence: high
source: plan-retrospective (aspect: routing-decisions)
suggested_epic: truthful-signals (audit layer emits a confident FAIL on a clean fact — not a PR/review finding)

## Context

`check-routing-decisions` reported `mis_prune:sonar-roundtrip = fail` — "sonar-roundtrip skipped as no_code_delta but the realized footprint touched production code". That verdict is false. sonar-roundtrip did not leave `phase_6.steps` because its prune predicate fired; it left because of the recorded posture cutoff. The script printed the proof in its own output: `recorded_lane_decisions[]` contains the exact line that names the cause.

## Root cause

`check-routing-decisions.py::_REMOVAL_CAUSE_PATTERNS['posture_cutoff']` matches:

```
lane_resolution\s+—\s+execution_profile=[^,]+,\s+dropped\s+(?P<steps>.+?)\s+from\s+phase_6\.steps\s+\(tier above posture cutoff\)
```

The live emitter writes:

```
[STATUS] lane_resolution — dropped sonar-roundtrip from phase_6.steps (execution_profile=standard): effective tier full exceeds the standard posture cutoff
```

Two independent mismatches: the field order is inverted (step before profile, not profile before step), and the trailing literal `(tier above posture cutoff)` was replaced by `: effective tier full exceeds the standard posture cutoff`. `resolve_removal_causes()` therefore returns `{}` for the step, `log_readable` stays `True`, and the code falls through to predicate re-evaluation — the exact path the function's own docstring calls "a fabricated `fail`".

The script carries an explicit `RE-DERIVATION OBLIGATION` comment above `_PRUNABLE_PREDICATES` binding the removal-cause set to the emitter contract in `manage-execution-manifest/standards/decision-rules.md`. The emitter's line shape drifted (plausibly with the `auto` -> `standard` posture rename in #1068) and the consumer regex was not re-derived. The obligation was written down and still not discharged, because nothing mechanically couples the two sides.

## Blast radius

Every `execution_profile=standard` plan whose footprint touches production code gets a false `mis_prune` FAIL, and the reference contract tells the LLM that a `fail` row is "strong evidence of UNDER-PROVISIONED". Left alone this systematically biases the posture-verdict signal toward under-provisioned and would eventually drive a real threshold change off fabricated evidence.

## Proposed action

1. Re-derive all four `_REMOVAL_CAUSE_PATTERNS` against the live emitters (only `posture_cutoff` was verified drifted in this pass; the other three are unverified and MUST be re-checked, not assumed clean).
2. Add a coupling test that asserts every emitter's produced line is matched by its consumer pattern — construct the line from the emitter, not from a literal fixture, so a re-word breaks the test rather than the audit.
3. Fix `references/routing-decision-verification.md`: its posture vocabulary is `minimal | auto | full`, but the live `LANE_TIERS` is `('minimal', 'standard', 'full')`. The doc is stale from the same rename.

## Evidence

- aspect: routing-decisions — `mis_prune:sonar-roundtrip,fail,no_code_delta,predicate_evaluated`
- `.plan/local/plans/crashed-participation-gate-records-a-pass/logs/decision.log` line 34 — the verbatim emitted line
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-routing-decisions.py` lines 103-129 (`_REMOVAL_CAUSE_PATTERNS`), 384-419 (`evaluate_mis_prunes`)
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_lanes.py:19` — `LANE_TIERS = ('minimal', 'standard', 'full')`
