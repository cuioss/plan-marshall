envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=live-blockers
kind=finding
created=2026-10-23T11:47:49Z

# Request to prioritise (HIGH PRIORITY): a runbook-lane worktree has no executor, so every build runs in process; the epic that owns it is parked

Source: epic `pm-mcp-core-m2-m4`, 2026-10-23, from the landings of PLAN-96, PLAN-95, PLAN-25 and PLAN-26 (`/plan-marshall-runbook-lane` on opencode) and a read of the lane worktrees on disk. Requested by the operator ("ping plan-marshall to prioritize"). Priority: high.

## Observed

`executor_absent_from_worktree` is reported by every runbook landing of this epic since 2026-10-22, four in four:

| plan | pull request | what the landing reports |
|---|---|---|
| PLAN-96 | #143 | first routed gate failed, then `--timeout 3600` after a learned bound of 776 s expired mid-build |
| PLAN-95 | #144 | first routed job failed with exit 2 (job log `1785d760...`), every later build `in_process_fallback`; learned bound of 776 s hit after 3047 passing tests |
| PLAN-25 | #145 | same; bound of 617 s hit after 5266 passing tests, re-run with `--timeout 1800` |
| PLAN-26 | #146 | same; bound of 617 s hit after 5387 passing tests, re-run at 1200 s |

The build server was `ready` at every setup preflight, so the daemon was available and unused for all of these runs. The three lanes running on 2026-10-23 (PLAN-87, PLAN-94, PLAN-103) have worktrees that hold `local`, `marshal.json`, `orchestrator` and `project-architecture` and no `execute-script.py`. The worktree of PLAN-28, started the same day, did not exist yet when checked.

## Cause (read, not assumed)

- `.plan/execute-script.py` is untracked (`.gitignore` line 17 ignores `.plan/*`), so a git worktree never carries it.
- `worktree-create` makes `.plan/local` and nothing else (`git-workflow.py` `_materialize_local_dir`). The executor is generated into a worktree by `prepare_execute` at the plan lifecycle's phase-5 move-in (`_executor_slot.py` names both producers), and the runbook lane never runs that step.
- `runbook-lane/SKILL.md` § 2 says a routed job re-runs the worktree's own executor, "which worktree creation supplies". It supplies none.
- Your own record already has this: PLAN-LB-73 (decide whether the lane materialises the executor or checks for it before the first routed build), the bootstrap defect with owner PLAN-LB-89 (`generate_executor.py`, "parked by the focus rule", medium) and the landing of PLAN-LB-78 (the routed job ends terminal, no fallback runs).

## Request

Raise PLAN-LB-89, or the part of PLAN-LB-73 that decides this, out of the parked state, and rate the defect high rather than medium:

1. It is not a rare bootstrap case. It happens on every run of the runbook lane that builds, in every consumer epic that uses the lane, which is what this epic's four landings show.
2. The cost is paid in every run: the build daemon the operator started is never used, each lane falls back by hand to `--execution-mode in_process`, and the learned supervisory bound (617 to 776 s) expires on a full `verify` that then needs a second, longer run.
3. The fix is small compared with that cost: either the lane's setup generates the per-tree executor (the `prepare_execute` step, which `generate_executor --marketplace-root` already implements) or `worktree-create` does.

## Not part of this request

No consumer-side change is needed in `pm-mcp-core`. This epic will drop the Watch on `executor_absent_from_worktree` when a lane worktree starts with the executor present.
