envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-corpus-group-contamination
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T08:05:15Z

# Candidate lesson: Re-record change-ledger rows when a sync-baseline rebase rewrites commit SHAs (plan-marshall:phase-6-finalize)

Forwarded from pm-mcp-core, plan corpus-group-contamination (PR plan-marshall/pm-mcp-core#86, merged e935da3), archived at pm-mcp-core/.plan/local/archived-plans/2026-10-18-corpus-group-contamination. The pm-mcp-core lesson store refused it as wrong_store (it names a plan-marshall component).

### Observation

finalize-step-sync-baseline rebased the branch onto origin/main after execute had written the change-ledger rows. The loop-back 5-execute -> 6-finalize transition was then refused with `execute_commits_unrecorded` for 5 of 6 commits, and the rows had to be re-recorded by hand (the manual Step 10a settlement). Retrospective confidence: high (script_failure_analysis, chat_history_analysis, llm_to_script_opportunities).

### Candidate rule (for orchestrator classification)

A rebase in sync-baseline must carry the ledger with it: add a `manage-change-ledger` rebind-after-rebase verb that maps old to new SHAs by patch-id and appends the rows, and have finalize-step-sync-baseline call it itself.
