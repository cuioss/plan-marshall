envelope_version=1
sender_type=plan
sender_id=worktree-executor-root-resolution
epic=multiplattform
kind=landing
created=2026-09-07T21:59:59Z

```landing-facts
schema=landing-facts/1
plan_id=worktree-executor-root-resolution
epic=multiplattform
pr=#1444
merge_state=merged
deliverables_total=2
deliverables_done=2
total_tokens=unknown
steps=step-4-implement:done,step-5-build-gate:done,step-6-verifier:clear,step-7-pr:done,step-8-merge:done,step-9-self-check:done
```

PLAN-21 landed. PR #1444 merged via the merge queue as commit `64733323a`. Deliverables: D1 (detectable worktree-escape executor resolution — `WorktreeEscapeWarning` from `get_executor_path`, remedy `PLAN_TRACKED_CONFIG_DIR` now honored) and D2 (documentation in `doc/developer/repository-layout.adoc`). Full `verify` green (20736 tests on the merged tree). CodeRabbit reviewed and its one Major finding was fixed and confirmed resolved; Sourcery approved; cuioss-review-bot clean.

Out of the ordinary: the CodeRabbit per-developer quota stalled the first PR (#1439) for hours; at operator direction it was closed without merging and reopened as #1444, where the quota had cleared. Full narrative and the two contract-change proposals (project-dir absolute-form; basetemp geometry) are in the run report at `.plan/local/oc-plans/multiplattform/210-worktree-executor-root-resolution/report.md`; the operator approved shipping those two as a separate `chore/` PR.
