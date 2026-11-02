envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=lessons-routing
kind=finding
created=2026-10-27T14:51:14Z

# A worktree executor pinned to a version the plugin cache no longer holds cannot refresh itself

Source: API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-06-enumeration-hardening (PR #528), candidate lesson 004. Observed with plugin 0.1.2017 in the cache.

## Observation

The plan worktree's `.plan/execute-script.py` pinned plan-marshall 0.1.2010 while the cache held only 0.1.2017. `build_server wait` failed with `ModuleNotFoundError: _build_server_protocol`. `worktree-executor-refresh` could not repair it, because that verb runs through the same stale executor and failed on a missing `triage_helpers`. Running the newest cached generator directly (`generate_executor.py recover --project-dir <worktree>`) worked. This recurs the earlier executor version-skew finding (2026-10-13-07-001).

## What to consider

- Detect a pinned version missing from the cache at executor start-up and print the direct `generate_executor.py recover` command, instead of failing later inside an arbitrary module import.
- The refresh path must not depend on the executor it is meant to repair.
