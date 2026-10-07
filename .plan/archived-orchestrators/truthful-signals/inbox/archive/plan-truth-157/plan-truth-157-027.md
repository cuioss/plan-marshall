envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:04:25Z

component=plan-marshall:manage-config
category=improvement
bundle=plan-marshall

# A hardcoded surface list lets a newly registered surface stay unpinned while every assertion keeps passing

CodeRabbit review-body nitpicks on PR #1494, both instances of one shape: hardcoded
enumerations of the orchestrator dispatch surfaces, which drift when a new surface is
registered and leave it unpinned and untested.

Sites named: `test/plan-marshall/manage-config/test_config_defaults.py:2025` (tuned
effort surface keys) and `test/plan-marshall/manage-config/test_orchestrator_scope.py`
at 620 and 645 (the pinned-surface and unpinned-surface tests). A second nitpick asked
for the seven-entry dispatch index in `orchestration-model.md` to be DERIVED from the
verb documents and compared against the index, with a non-empty assertion on the
derived population so the check cannot pass vacuously.

Source record: pr-comment finding `5bea99`, PR #1494, bot `coderabbit`, `review_body`,
resolution `fixed` (remediated in-run by TASK-007).

## Solution

Replace the hardcoded set at all three sites with the authoritative registered
surface set, so a newly registered dispatch surface cannot stay unpinned while the
assertions keep passing. Derive the seven logical dispatch entries from both verb docs
(five from `analyze.md`; two from `decompose.md`, whose Step 2 envelope carries both
the read and the returned spec-body draft), assert the derived population is
non-empty, and compare it with the index.

Keep the existing `_PROJECT_TUNED_ORCHESTRATOR_KNOBS` VALUE pin: the new check guards
the surface SET and composes with the value pin rather than replacing it. A set guard
and a value guard answer different questions and neither substitutes for the other.

## Impact

Same root rule as the sibling candidate on chained populations, reached from the
opposite direction: here the population was hardcoded rather than derived. Both make a
green assertion compatible with an untested member. Worth noting that a review bot
filed this as a "trivial / nitpick" — the severity label understates it, because the
failure mode is silent loss of coverage rather than a visible defect.
