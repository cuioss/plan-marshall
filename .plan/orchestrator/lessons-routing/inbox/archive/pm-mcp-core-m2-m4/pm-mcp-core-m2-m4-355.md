envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T15:13:52Z

# Functional-review verdict schema has no "superseded" status for a single criterion

**Component:** plan-marshall:phase-6-finalize functional-review (verdict schema, `review_support validate`)
**Category:** improvement
**Source plan:** plan-14-operator-and-question-stores, from plan-retrospective

## Observation

After the operator ruled that the `BROKEN LINKS 0` criterion of D8 was superseded (the link check was removed by #88), the functional-review leaf had no way to record that. The schema allows `superseded_by` only on a deliverable row, and superseding the whole D8 would drop its other criteria. Each later round therefore recorded the criterion as `not_met`, with a non-consequential residual explaining that "`not_met` is only the schema's stand-in for superseded". The same workaround was re-justified in four more rounds and verifier spot-checks.

## Suggested corrective action

- Allow `status: superseded` with a `superseded_by` reference (an operator decision id or commit) on a criterion row. The validator treats it as neither met nor a finding, and the report shows it as its own state.
