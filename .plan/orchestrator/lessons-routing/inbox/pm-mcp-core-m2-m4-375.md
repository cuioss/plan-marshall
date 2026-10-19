envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T18:47:05Z

component=plan-marshall:phase-6-finalize
category=improvement

# Criterion about the plan's own PR body cannot be evidenced by a review that runs before the PR body is written

Source: Q-Gate 6-finalize finding 82db0b (functional-review, unevidenced_criterion at D10.C3; resolved in run as accepted), plan plan-70-plan-instance-alignment.

D10.C3: "the roadmap-link pull request in plan-marshall-documentation is open and named in this plan pull request body". At the review head no branch/PR existed yet, and the plan PR body is written after the functional review by design - so the criterion is structurally unevidenceable at review time and always needs an operator acceptance.

## Rule

Do not write success criteria whose evidence is the plan's own PR body (or any artifact finalize writes after the functional review). Either evidence them in-tree (e.g. a recorded cross-repo PR reference in the plan) or make them a PR-body checklist item that the PR-creation step verifies.
