envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T07:42:11Z

# Candidate lesson: worktree-rebase-to executor drift probe returned no usable verdict

Source: script failure cluster. The executor drift probe of `worktree-rebase-to` returned no usable verdict.

During finalize the drift probe that `worktree-rebase-to` runs against the executor produced no verdict the caller could branch on. The rebase path therefore ran without a confirmed drift answer.

Candidate rule / fix direction: the drift probe must always return a closed-vocabulary verdict (drifted / current / unknown with a reason), and the caller must handle the unknown arm explicitly instead of receiving an unusable result. Check whether the probe depends on worktree-local state that the merge-queue flow does not produce.

Scope hint: plan-marshall framework (workflow-integration-git worktree verbs). Details were not reconstructed in this envelope; the orchestrator should check the plan's script-execution log for the exact output.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-04-service-unit-010.md` from plan plan-04-service-unit (PLAN-04, #25)
