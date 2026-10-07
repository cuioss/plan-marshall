envelope_version=1
sender_type=plan
sender_id=wrong-store-guard-refuses-project-local-lessons
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T11:56:26Z

component=plan-marshall:manage-lessons
category=improvement
created=2026-07-29

# Suspected split derivation of a guard turned out to be a false alarm

The spec for `wrong-store-guard-refuses-project-local-lessons` hypothesized that `manage-lessons.py:399` and `:797` each carried their own derivation of the store-ownership check, risking a half-live-defect if only one copy got fixed. Investigation at outline REFUTED this: both call sites route through one shared `guard_component_store_match` helper — the split exists exactly once.

## Impact

A spec-stated hypothesis about duplicated logic is a claim to verify, not a fact to build the fix plan around. This one turned out false and cost nothing because outline checked it before planning committed to a dual-site fix; a future spec asserting "N call sites carry N derivations" should get the same read-the-actual-call-graph check before the plan sizes itself around the duplication.
