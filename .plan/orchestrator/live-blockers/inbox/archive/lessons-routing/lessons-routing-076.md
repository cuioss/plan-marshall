envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-02T16:42:24Z

Severity: HIGH (operator-graded 2026-11-02). Bundle: plan-marshall (script-shared build routing, manage-status). Checked at f6830b837.

A daemon-routed build run with `--plan-id` after the plan's worktree contents were moved back (integrate into main) and before the worktree is removed fails inside the daemon with `worktree_resolution_failed`, but surfaces to the caller as a generic `build_failed` carrying a synthetic "no structured errors were parsed" row. A routing failure is reported as a red build, and the factory docstring's invariant that `--plan-id` "resolves identically in both processes" is false. Read from code; not reproduced by an executed run.

Ground-truth evidence:
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py:1036-1047` re-runs the executor under the daemon with the original `sys.argv[1:]`, rewriting only `--project-dir` (`_absolutise_project_dir`); `--plan-id` is passed through unchanged. The docstring around `:932-935` claims `--plan-id` resolves identically in both processes.
- `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_status_query.py:676-683` documents that `get-worktree-path` deliberately keeps the STRICT gate with no sibling-worktree fallback. The inner process runs with cwd = the worktree, where the plan directory is absent after move-back, so resolution fails.
- The outer wrapper folds the failure into `build_failed`: `LAUNCH_FAULT_ERRORS` is only `{execution_failed, log_file_failed}` (`_build_result.py:267`) and the synthetic row is emitted at `_build_shared.py:1040-1049`.
- A direct, non-routed build reports `worktree_resolution_failed` as its own error with exit 2 (`_build_cli.py:683-689`), so the misattribution is specific to the routed path.
- Narrowing facts (the reason this was a borderline grade): the window is between move-back and worktree removal, only for daemon-routed builds, the failure is immediate, and `--project-dir` is a workaround.

Source lessons:
- API-Sheriff 2026-08-09-03-002

Full body: `lessons-archive/filed-live-blockers/sweep-2026-11-02/API-Sheriff/2026-08-09-03-002.md`
