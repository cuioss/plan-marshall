envelope_version=1
sender_type=plan
sender_id=daemon-baseline-interpreter-is-unregistrable
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T21:07:09Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_aspects=manifest-decisions,routing-decisions

# Manifest cross-check M3 compares a bare step id against the canonical verify: form

## Context

`check-manifest-consistency.py` exists to catch a manifest whose phase-5 verification was narrowed to tests-only while the realized diff contains production source. In this plan it reported `passed: 2, failed: 0, findings: 0` — a clean pass — over exactly that violation.

`evaluate_tests_only` (line 324) gates on `steps != ['module-tests']`. The composer never emits that value: `_manifest_decide._decide` Rule 4 narrows phase-5 by matching each candidate's `_role_of(...) == 'module-tests'` and keeps the candidate's canonical id, which is `verify:module-tests`. The rule therefore always takes the skip branch and emits `rule M3 not applicable — verification_steps != ["module-tests"]`, even though the decision log on the same run says `Rule tests_only fired`.

Re-run against the true 9-file footprint from squash commit `263f216d9`, M3 still skips. Had the predicate matched, its culprit set would have been `marshalld.py` and `_marshalld_verifier.py` — two production source files — producing a `tests_only_diff_violation`.

## Root cause

The consumer pinned a literal step-id string while the producer's step-id vocabulary gained a `verify:` prefix. Nothing tests the agreement, and the skip path is indistinguishable from a genuine not-applicable, so the guard died silently.

## Proposed action

Compare on the trailing canonical segment using the same `_role_of` / `_CANONICAL_TO_ROLE` mechanism the composer already uses to SELECT the step, so consumer and producer cannot drift again. Add a test that composes a real tests-only manifest and asserts M3 evaluates rather than skips — the current test at `test/plan-marshall/plan-retrospective/test_plan_retrospective_manifest.py` uses the bare `module-tests` form and so passes while production is dead.

Consider also making a skip that no plan can ever reach a reportable condition: a predicate whose skip branch fires on 100% of runs is a defect, not a pass.

## Evidence

- aspect: manifest-decisions — `tests_only_diff,skip,"rule M3 not applicable — verification_steps != [\"module-tests\"]"` alongside manifest `verification_steps[1]: - "verify:module-tests"`
- decision.log `1c81ad` — `Rule tests_only fired — phase_5.verification_steps=['verify:module-tests']`
- `check-manifest-consistency.py:324` — `if not isinstance(steps, list) or steps != ['module-tests']:`
- `architecture search --content --pattern 'verify:module-tests'` returns 85 files; `check-manifest-consistency.py` is not among them
