envelope_version=1
sender_type=plan
sender_id=implement-plan-09-interaction-mode
epic=operator-ux
kind=candidate-lesson
created=2026-09-16T16:13:44Z

component=plan-marshall:plan-retrospective:collect-fragments
category=bug

# Resolve fragment paths against a single plan root

Source: work-log script_failure 2026-09-16T15:59:09Z, notation plan-marshall:plan-retrospective:collect-fragments exit 1, missing fragment-artifact-consistency.toon under a doubled .plan/local/plans path.

Defect: the fragment resolver joined the plan directory against an already plan-rooted base, producing .plan/local/plans/<id>/.plan/local/plans/<id>/work/fragment-artifact-consistency.toon.

Rule: resolve plan-relative artifacts through one plan-context resolver; never join a plan dir that already carries the store prefix.

Evidence: the doubled prefix is visible verbatim in the failure detail, so the join site is unambiguous.
