envelope_version=1
sender_type=plan
sender_id=lb-25-phase-and-merge-gates
epic=live-blockers
kind=candidate-lesson
created=2026-10-11T16:01:14Z

component=plan-marshall:phase-6-finalize
category=bug
bundle=plan-marshall
source_plan=lb-25-phase-and-merge-gates

# Run root-level test guards before push when scoped module-tests pass

## Context

Every local gate in lb-25-phase-and-merge-gates passed, yet CI failed on `test/test_harness_shape_guards.py::test_no_runtime_derived_parametrize_is_unguarded` (rule R5): two `@pytest.mark.parametrize('route', gate.ROUTES)` sites had no non-empty guard. The file sits at the root of `test/`, outside the `plan-marshall` module, so `module-tests plan-marshall` never runs it. The finalize pre-push quality gate resolved `divergence_possible=false`, so its whole-tree run was skipped. A later round hit the same class again: a no-historical-prose violation in a doc edit was caught only by the whole-tree `test_real_marketplace_quality_gate_has_zero_findings`, not by `quality-gate plan-marshall`.

## Root cause

Scoped module runs exclude the root-level `test/` guards that apply to every module, and the pre-push gate treats a green scoped run as sufficient when it judges divergence impossible.

## Proposed action

Make the scoped `module-tests {module}` run (or the pre-push gate) always include the root-level `test/*.py` shape and marketplace-wide guards, or make the pre-push gate run them unconditionally whenever a plan adds or edits test files. Record the excluded population so a scoped green run states what it did not cover.

## Evidence

- aspect: chat_history_analysis - "test/test_harness_shape_guards.py sits at the root of test/, outside the plan-marshall module. module-tests plan-marshall never runs it; only a whole-tree run does"
- aspect: chat_history_analysis - "quality-gate plan-marshall did not catch that wording; only the whole-tree test test_real_marketplace_quality_gate_has_zero_findings did"
- aspect: plan_efficiency - the CI round trip added an execute re-entry to a plan already over its token anchor
