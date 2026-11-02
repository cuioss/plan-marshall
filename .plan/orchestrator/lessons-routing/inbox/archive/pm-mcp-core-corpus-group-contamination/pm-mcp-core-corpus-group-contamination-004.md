envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-corpus-group-contamination
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T08:05:15Z

# Candidate lesson: Record an execute dispatch that ends in a refused transition as error (plan-marshall:plan-marshall)

Forwarded from pm-mcp-core, plan corpus-group-contamination (PR plan-marshall/pm-mcp-core#86, merged e935da3), archived at pm-mcp-core/.plan/local/archived-plans/2026-10-18-corpus-group-contamination. The pm-mcp-core lesson store refused it as wrong_store (it names a plan-marshall component).

### Observation

The execute dispatch returned status error `execute_commits_unrecorded` (the refused transition of lesson 001), yet the dispatch-boundary ledger recorded its termination cause as `clean_exit_queue_empty`. Retrospective confidence: medium (logging_gap_analysis).

### Candidate rule (for orchestrator classification)

A dispatch whose last result is an error or a refused transition is recorded with termination cause `error`, never as a clean exit.
