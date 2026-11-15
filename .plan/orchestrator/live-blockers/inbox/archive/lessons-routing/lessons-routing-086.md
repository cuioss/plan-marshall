envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-10T17:35:43Z

# A build-server submit with no plan selector builds the main checkout and reports success for the wrong tree

**Severity:** high (operator grade, 2026-11-10 ingest of this repository's own lessons corpus)
**Bundle:** plan-marshall (`build-server-client`)
**Checked at:** `e7033b83a` (origin/main)

## What was reported

API-Sheriff plan `plan-23-session-route-scope-parity`, 2026-10-01: the module-tests build for one task was submitted to the build server with `--project-path` for the main checkout and no plan or project selector in the inner command. The job returned `success` after about twelve minutes, and it had built the MAIN checkout, not the plan's worktree: the log was written under `plans/NO_PLAN` and it compiled 199 main sources and none of the plan's new test classes. The result was discarded only because the orchestrator read the log path and the source count; the job status, the wait result and the work-log line were identical to those of a correct build. A resubmit with `--plan-id` in the inner command ran the worktree (4053 tests).

A green result for a tree that does not contain the change would have closed that task's verification without one of its tests having run.

Lesson's own proposals: the submit or wait reply states which tree was built (project path and tree hash) and the caller compares it with the plan's worktree; a submit for a plan that has a worktree whose inner command resolves to the main checkout is refused or answered with a warning.

## Ground truth at the checked commit

`marketplace/bundles/plan-marshall/skills/build-server-client/scripts/build_server.py`:

- `:436` sets `exec_path = args.exec_path or project_path`, and the job spec is built from the caller's command as given (`:437-452`); nothing compares it with a plan worktree.
- `:498-520` the submit reply carries `status`, `job_status`, `job_id`, `attached` and the job running in the same directory. It names no built-tree path or hash.

So the described behaviour follows from the code as read. NOT verified: the daemon-side tree resolution, and whether a plan-less submit for a plan that has a worktree is refused anywhere on the daemon.

## Relation to filed and shipped work

- The wrapper path, which routes by plan id, is covered by PLAN-LB-104 (routed-build-project-dir), PLAN-LB-112 and PLAN-LB-115 (routed-build fault truth and carry). This finding is the RAW submit, which those do not cover as far as this index shows.
- `lessons-routing-076` (a routed build misreports a routing failure as `build_failed`) and the earlier medium subject "fix-round builds filed under NO_PLAN" are neighbours. Please check them before opening new work.

## Source

- Local lesson `2026-10-02-13-005`, archived verbatim at `lessons-routing/lessons-archive/filed-live-blockers/2026-10-02-13-005.md`.
