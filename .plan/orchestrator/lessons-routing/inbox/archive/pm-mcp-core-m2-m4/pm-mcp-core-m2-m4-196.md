envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T08:39:53Z

## Candidate lesson: Sourcery review-budget notice not recognised as a refusal

Source: automatic-review step (signal_automated_review_count = 1).
Plan: static-verifier-rule-gaps-completion (PR #48, merged as 36a0bcd).
Owning component (suggested): plan-marshall:automatic-review (standards/sourcery.md, refusal_patterns), consumed by plan-marshall:workflow-integration-github fetch_findings.

Observation: Sourcery posted a notice that it had "used its review budget of 2,500,000 diff characters for the last 7 days" instead of a review. fetch_findings did not recognise this as a refusal, so the review was not reported as refused. The budget notice is probably missing from the Sourcery refusal_patterns.

Suggested fix: add a pattern for the Sourcery review-budget notice to refusal_patterns in automatic-review/standards/sourcery.md, with a test that a comment of this shape is classed as a refusal.

This belongs to the plan-marshall repository, not pm-mcp-core.

Classification deferred to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `static-verifier-rule-gaps-completion-007.md` from plan static-verifier-rule-gaps-completion (PLAN-54, #48; Claude Code)
