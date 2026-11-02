envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-corpus-group-contamination
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T08:05:15Z

# Candidate lesson: Match the Sourcery review-budget notice in refusal_patterns (plan-marshall:automatic-review)

Forwarded from pm-mcp-core, plan corpus-group-contamination (PR plan-marshall/pm-mcp-core#86, merged e935da3), archived at pm-mcp-core/.plan/local/archived-plans/2026-10-18-corpus-group-contamination. The pm-mcp-core lesson store refused it as wrong_store (it names a plan-marshall component).

### Observation

Sourcery answered with "used its review budget of 2,500,000 diff characters". The notice was not matched by `refusal_patterns`, so it was filed as an ordinary review finding and later read as a decline, which escalated the re-review to the operator. The operator then chose to proceed without Sourcery. Retrospective confidence: high (chat_history_analysis, log_analysis).

### Candidate rule (for orchestrator classification)

A review-budget notice from an optional bot is a refusal (quota state), not a finding: add it to `refusal_patterns`, and let automatic-review proceed without the optional bot instead of escalating. Related: the API-Sheriff CodeRabbit rate-limit lesson (api-sheriff-api-sheriff-0-2-0-001).
