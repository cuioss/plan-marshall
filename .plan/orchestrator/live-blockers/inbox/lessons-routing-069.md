envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-02T11:19:19Z

# The build daemon runs two builds in one worktree at once, and the shared `target/` produces false build failures

Severity: **high (operator ruling, 2026-11-02 cross-repo sweep)** against a medium default: build-daemon routing is now the default lane (PLAN-LB-104), so every caller is exposed. Bundle: `plan-marshall` (`manage-build-server` / build daemon scheduling; `manage-locks` build-queue limiter).

## Source

- API-Sheriff lesson `2026-10-04-09-002`, verbatim in `lessons-routing/lessons-archive/filed-live-blockers/sweep-2026-11-02/API-Sheriff/2026-10-04-09-002.md`. Observed twice: PLAN-V02-10 (#382, 2026-10-03) and PLAN-V02-14 (#387, 2026-10-06).

## Observation

1. Two Maven jobs for the same plan worktree were submitted 4 s apart. The daemon's machine-global `max_slots=2` let both run together. One failed with a false ClassNotFoundException / NoClassDefFoundError, the other passed; both wrote the same `target/`.
2. Recurrence: module tests (`test -pl api-sheriff -am`) and integration tests ran concurrently in one worktree. A different set of Quarkus tests failed with "Failed to start quarkus" in each run; serial re-runs were green. It was accepted as concurrency-induced and cost a loop-back.

The lesson's own conclusion: the rule is known but nothing enforces it at dispatch time.

## Ground truth (c431a8193)

No plan-marshall script keys any build exclusion on `project_dir` / worktree (content search over the scripts). The slot cap limits builds machine-wide only. Not reproduced here.

## What to consider

- Serialize jobs that share a project directory (a per-worktree build lock, or a per-project_dir queue in the daemon), and spend slots only across different directories.
- Until then, refuse or queue a second submission for a worktree that already has a running job, and say so in the submit result.
