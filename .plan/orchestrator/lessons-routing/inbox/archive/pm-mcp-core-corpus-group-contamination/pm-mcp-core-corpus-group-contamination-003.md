envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-corpus-group-contamination
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T08:05:15Z

# Candidate lesson: Emit the [OUTCOME] Completed line for tasks closed after orchestrator-tier verification (plan-marshall:phase-5-execute)

Forwarded from pm-mcp-core, plan corpus-group-contamination (PR plan-marshall/pm-mcp-core#86, merged e935da3), archived at pm-mcp-core/.plan/local/archived-plans/2026-10-18-corpus-group-contamination. The pm-mcp-core lesson store refused it as wrong_store (it names a plan-marshall component).

### Observation

TASK-002, TASK-003 and TASK-004 stayed open with verification owed to the orchestrator tier and were closed later outside the execute-task completion path, with only Per-deliverable commit lines. [OUTCOME] coverage reads 5 of 8 done tasks (ERROR, lesson 2026-05-08-14-001 class). Retrospective confidence: high (logging_gap_analysis, log_analysis).

### Candidate rule (for orchestrator classification)

Every path that sets a task to done writes its [OUTCOME] Completed line, including the close after orchestrator-tier verification; the close should go through the same completion call rather than a bare status change.
