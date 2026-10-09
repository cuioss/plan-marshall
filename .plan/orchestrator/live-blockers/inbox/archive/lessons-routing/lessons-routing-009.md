envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-09T15:43:58Z

# The main checkout's executor can point into a removed worktree

- **Severity:** high (every script call from the main checkout fails until the executor is regenerated)
- **Bundle:** `plan-marshall` (`tools-script-executor`)
- **Source lesson:** `2026-10-09-13-004`
- **Full body:** `lessons-routing/lessons-archive/filed-live-blockers/2026-10-09-13-004.md`
- **Filed by:** the `ingest` run of `lessons-routing`, 2026-10-09 (second run). The lesson is retired from the corpus.

## What the lesson says

After `integrate_into_main` on PLAN-LB-23 the main checkout's `.plan/execute-script.py` failed with
`ModuleNotFoundError: plan_logging`: its bootstrap paths pointed into the removed worktree of
another plan, and the cache self-heal did not recover it. Proposed: bind the generated bootstrap
paths to the checkout the file is written into; make the self-heal regenerate when a bootstrap path
does not exist; add a test (generate from a worktree, remove the worktree, run the main executor).

## Owner today

None. It is your Open Defect "The main checkout's executor can be left pointing into a worktree
that no longer exists", which cites this lesson as carrying the proposal. The lesson now lives at
the archive path above.

## Asked of live-blockers

Decide whether to stage it. Not reproduced and not re-checked in code at this run; the lesson
itself rests on the PLAN-LB-23 orchestrator's account.
