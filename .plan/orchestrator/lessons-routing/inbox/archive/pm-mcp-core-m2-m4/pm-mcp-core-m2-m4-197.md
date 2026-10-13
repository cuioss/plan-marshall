envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T08:39:53Z

## Candidate lesson: pre-push quality gate red after rebase onto a sibling plan, plus build timeout too short

Source: script-failure cluster (signal_script_failure_clusters_count = 1), the build wrapper plan-marshall:build-maven:maven during finalize.
Plan: static-verifier-rule-gaps-completion (PR #48, merged as 36a0bcd).

Two observations from the same cluster:

1. Sibling plan landed on shared code while this plan was running. In finalize the branch was rebased onto #45 (workflow engine: state machine interpreter and workflow state store). After the rebase the pre-push quality gate failed: a compile break on VerificationResult, and 39 engine tests from #45 were now refused by the stricter verifier this plan added. Both plans touched the verifier and the workflows it checks, and neither plan's checks saw the other's change.
   - Suggested rule (epic level): when two plans in the epic share a surface (here the verifier and the workflow definitions it validates), either order them in the queue or have the later plan rebase onto the earlier one and run the full verify before finalize, not only at pre-push.
   - Suggested check: a plan that makes a validator stricter re-runs the validator over all current content after rebasing, since content added by sibling plans may now fail.

2. Build timeout too short. The default build-wrapper timeout of 300 s was below the run time of verify -Ppre-commit (366 s), so the quality gate run hit the timeout.
   - Suggested fix: raise the timeout the build wrapper uses for verify -Ppre-commit in this project (for example through the architecture-resolved bash_timeout_seconds for that command), so it lies above the measured 366 s with headroom.

Classification deferred to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `static-verifier-rule-gaps-completion-008.md` from plan static-verifier-rule-gaps-completion (PLAN-54, #48; Claude Code)
