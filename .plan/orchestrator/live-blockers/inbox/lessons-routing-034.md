envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-15T12:34:18Z

# Lessons ingest: triage fix-task shape under deliverable 0 rejected by commit-add (recurrence of -020)

Severity: high (prior ruling: fix tasks under deliverable 0 = high; recurrence of `lessons-routing-020`). Bundle: `plan-marshall` (`phase-6` triage template, `manage-tasks` validator).

Source: pm-mcp-core epic `pm-mcp-core-m2-m4` inbox message `-230`. Full body: `lessons-routing/lessons-archive/filed-live-blockers/pm-mcp-core-m2-m4-230.md`.

| Message | Statement |
|---|---|
| `pm-mcp-core-m2-m4-230` | Triage fix-task template output under `deliverable: 0` rejected twice by the task validator. |

Asked for: same as `-020` (triage emits a committable shape, or the validator accepts the triage shape); check against `-020` for residual.

Owner today: nearest PLAN-LB-26. Not re-checked at HEAD by the ingest.
