2026-10-05 — PRE-ARCHIVE CLEANUP DONE. Queue terminal: 7 shipped (PLAN-01/02/04/08/09/10/11), 4 superseded by PM-MCP (PLAN-03/05/06/07). All open items transferred (truthful-signals, review-apparatus, lessons-routing — orchestrator-refactor-001.md each) or resolved; settled narrative relocated to settled.md (see Decisions 2026-10-05). Inbox empty; restart verdict ready.

Next action: operator runs /sync-harnesses (retires the last Watch), then /plan-orchestrator close → archive → land. Note for land: remote chore/orchestrator-ledger carries post-run-quality PRQ-15 commits the local worktree lacks (remote_branch_contained=false).

LEDGER LIVES IN THE SHARED WORKTREE (orchestrator.use_worktree ON): take epic_dir/store_checkout from resolve-path; ledger reaches main only through /plan-orchestrator land.
