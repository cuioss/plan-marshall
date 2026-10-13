envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-12T13:53:22Z

# Lessons ingest: triage files fix tasks under deliverable 0, which commit-add rejects; fix tasks get no envelope

Severity: high (backlog § 1.6). Bundle: `plan-marshall` (`manage-tasks`, `plan-marshall/workflow/triage.md`, `verification-feedback.md`, `phase-5-execute`).

Source: pm-mcp-core epic `pm-mcp-core-m2-m4`, six plans — every plan with a review-fix round. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/`.

| Message | Plan | Statement |
|---|---|---|
| `pm-mcp-core-m2-m4-025` | #20 | Triage prescribes `deliverable: 0`; commit-add refuses it. |
| `pm-mcp-core-m2-m4-054` | #26 | Refused in all three triage runs; leaves attributed fix tasks to the "closest" deliverable (TASK-32 under D8 while editing D7 files). |
| `pm-mcp-core-m2-m4-062` (item 3) | #28 | Same; items 1–2 (no `--task-number` on `manage-findings resolve`, router `--plan-id` placement) are low and archived with it. |
| `pm-mcp-core-m2-m4-087` | #31 | Same. |
| `pm-mcp-core-m2-m4-113` | #29 | Same; misattribution skews per-deliverable metrics and commit chaining. |
| `pm-mcp-core-m2-m4-117` | #32 | Same ("Missing required field: deliverable"). |
| `pm-mcp-core-m2-m4-006` | #18 | Fix tasks TASK-10..17 carry no `envelope_id` and no cost size; the hand-off had to be told by prompt to run them as one group. |

Ground truth at `fc0090a24`: `plan-marshall/workflow/triage.md:197` prescribes `deliverable: 0`; `manage-tasks/scripts/_tasks_core.py:882-886` raises `Missing required field: deliverable` for `0` unless `origin` is `holistic`. **Still present.**

Owner today: PLAN-LB-26 (`execute-loop-triage`, staged) — surface includes `_tasks_core.py`, `_tasks_envelope.py` and `triage.md`. The live-blockers resume anchor already says to re-ground LB-26 before launch.
