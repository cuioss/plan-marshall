envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-25T22:12:15Z

# Candidate lesson: a plugin-cache version move mid-run leaves the worktree executor failing with "Unknown notation" (plan-marshall:tools-script-executor, executor staleness)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-27-test-simplification (PR cuioss/API-Sheriff#520), inbox message plan-v02-27-test-simplification-008. Observed by the orchestrator; the plan logs hold no entry for it. It is one of the six script-failure clusters the dispatcher counted (`signal_script_failure_clusters_count: 6`).

What happened: the plugin cache moved from 0.1.1986 to 0.1.2010 while the plan ran. The worktree's copy of `.plan/execute-script.py` kept the old notation mapping, so calls began failing with "Unknown notation" and kept failing until the executor was regenerated. Nothing flagged the skew beforehand.

Suggested direction:
- Let the executor detect that its pinned cache version is no longer the active one and fail with one actionable "executor stale, regenerate" error, not a per-notation "Unknown notation".
- Check (or regenerate) the worktree executor at each phase boundary and at loop-back re-entry, not only at worktree creation.

This is a third case beside the known ones: a stale executor regenerated through itself, and a missing executor in a new worktree. Here an executor went stale mid-run.
