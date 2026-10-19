envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T18:47:08Z

component=plan-marshall:phase-6-finalize
category=improvement

# A one-statement inline triage fix re-fired every HEAD-dependent finalize step and added an untested branch

Source: run observation reported by the orchestrator (finalize hook commit of a CodeRabbit-driven fix), plan plan-70-plan-instance-alignment.

The inline triage of CodeRabbit comment 187d38 committed a one-statement change to `PlanInstanceStore` (keep the refusal `Diagnostic` in the predecessor exception). Because every review is bound to HEAD, that one commit re-fired security-audit, functional-review and code-review (a delta round plus a closing round each), the pre-push gate, CI and both review-bot steps. The fix also added a new branch (`ParseResult.Refused`) with no test, which the re-fired reviews then flagged.

## Rules

- An inline triage fix that adds a code branch must add its test in the same commit; otherwise the re-review cascade it triggers exists mainly to report the missing test.
- Consider batching all triage fixes from one bot round into one commit, and letting a delta review whose diff touches only one method close in a single round instead of delta plus closing.
