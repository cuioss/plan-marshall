envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T15:13:50Z

# Head-dependent finalize steps re-fire on every HEAD advance; doc-only bot fixes cost hours

**Component (foreign):** plan-marshall:phase-6-finalize (security audit, functional review, code review, quality gate, bot and Sonar re-check steps; verdict_inputs), plan-marshall:automatic-review
**Category:** improvement
**Source plan:** plan-14-operator-and-question-stores (PR #93)

## Observation

Every head-dependent finalize step re-fires on every HEAD advance because the steps declare no `verdict_inputs`. A review-bot round whose fix is a one-line documentation change therefore re-runs the full security audit, functional review, code review and quality gate, costing hours per round. CodeRabbit raises new Minor wording remarks on each new head, so the loop only closed because the triage budget (3 rounds) and a documented accept policy bound it.

## Suggested corrective action

- Declare `verdict_inputs` per head-dependent step (path classes or file globs the verdict depends on) and re-fire a step only when the delta since its last verdict touches those inputs; e.g. a doc-only delta should not re-fire security audit or quality gate on code.
- Record the reason for each re-fire (which input changed) so the cost is visible.
- Keep the triage budget plus accept policy as the bound for bot loops, and document that Minor wording remarks on new heads are accept-by-policy after the budget.
