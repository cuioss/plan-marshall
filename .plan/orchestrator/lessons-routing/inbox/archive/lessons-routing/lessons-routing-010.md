envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=lessons-routing
kind=finding
created=2026-10-27T17:51:17Z

# Worktree executor not refreshed when the plugin cache upgrades mid-run (second plan in a row)

Source: API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-05-response-hygiene, candidate lesson 002. Recurrence of the finding routed from plan-v02-06 the day before.

## Observation

The plugin cache was upgraded during the run (0.1.2010, then 0.1.2017, then 0.1.2021). The worktree's `.plan/execute-script.py` stayed pinned to a version whose module layout had moved, so `git-workflow` failed with `ModuleNotFoundError: triage_helpers` (the module now lives under `script-shared/scripts/workflow`). Running the newest cached `generate_executor.py` directly inside the worktree fixed it. Two plans of one epic have now hit this in two days.

## What to consider

- Check a long-running worktree's executor against the active plugin cache at phase boundaries and at finalize entry, and regenerate it from the newest cached generator when it lags.
- Print the direct recover command when the pinned version is missing from the cache, and keep the refresh path independent of the executor it repairs.
