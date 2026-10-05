envelope_version=1
sender_type=plan
sender_id=cross-repo-telemetry-archive-and-analyze
epic=post-run-quality
kind=finding
created=2026-10-04T09:59:23Z
lifecycle=stream-end

Stream closed by the orchestrator on the landed plan's behalf, 2026-10-04. PLAN-PRQ-07 shipped as PR #1694 and its plan directory is archived at .plan/local/archived-plans/2026-10-04-cross-repo-telemetry-archive-and-analyze, so this sender cannot write again. All 9 of its messages (8 candidate-lesson, 1 landing) were drained and archived in the same pass. Filing this marker makes the queue report the FINISHED zero rather than the ambiguous EMPTY one.
