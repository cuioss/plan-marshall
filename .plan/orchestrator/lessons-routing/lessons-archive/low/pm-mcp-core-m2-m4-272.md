envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T06:32:44Z

> Routed by orchestrator epic pm-mcp-core-m2-m4 from plan plan-09-audit-trail (PLAN-09, pm-mcp-core #69, merged 3236ed5), drained 2026-10-15.
> Source inbox message(s): plan-09-audit-trail-002.md
> RECURRENCE of -072, -116, -157 (same invented verb). Earlier numbers are lessons-routing messages pm-mcp-core-m2-m4-NNN.

# Invented `manage-findings qgate query` verb during outline revision

- Source: script-failure cluster `plan-marshall:manage-findings:manage-findings` — work-log `[ERROR] ... script_failure` c3533b at 2026-10-14T08:42:02Z (phase 3-outline, revision dispatch after Q-Gate findings 2007e0 / f9ad42).
- Suggested component: `plan-marshall:phase-3-outline` (Q-Gate resolution step) / `plan-marshall:manage-findings` canonical invocations.

## Observation

`exit_code=2 failure_kind=argparse_rejection`: "`query` is not a registered verb for `manage-findings qgate`: ['add', 'clear', 'list', 'resolve', 'resolve-by-rule', 'resolve-evidenced']". The outline agent paraphrased the read verb (query) instead of using `qgate list --plan-id P --phase 3-outline --resolution pending`. Recovered in the same envelope; no data loss.

## Candidate rule

This is the known verb-paraphrase signature. If it recurs, the outline workflow's Q-Gate resolution step should quote the exact `qgate list` invocation inline (or xref the canonical block) at the point where the agent reads pending findings.
