envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T13:57:51Z

# Candidate lesson: a one-line fix loop-back re-fires the full review chain (verdict_inputs undeclared) (plan-marshall:phase-6-finalize (verdict_inputs / loop-back re-fire))

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-41-validator-asset-forwarding-anchor-rules (PR cuioss/API-Sheriff#489), source message 003.

Related (not a recurrence): archived pm-mcp-core-m2-m4-249 (re-check docs-only footprint before a loop-back rebuild).


rule, plan-marshall lessons belong in the plan-marshall repo's `lessons-routing` inbox (via that repo's
executor); only project lessons stay in this epic. Orchestrator: classify, dedup and forward.

Source: run fact reported by the finalize dispatcher (plan-v02-41, PR #489).

## Observation

After the review chain had closed, a Sonar new-code finding (java:S3776/S135 on a verbatim-moved method)
was fixed with a one-line change (two `continue` guards merged into one condition). The loop-back that
followed re-fired simplify, the security audit, functional + code review and the quality gate. Cause:
those steps declare no `verdict_inputs`, so every HEAD advance invalidates their verdicts regardless of
what the new commit touched. Cost: about 1.2M extra tokens for a single-line, behaviour-preserving edit.

Related: the code review's two advisories (ADR floor wording, stale ConfigValidator helper list) were
fixed by the orchestrator in a docs-only commit after the reviews closed — a docs-only HEAD advance that
under the same rule would also re-fire every review step.

## Candidate rule (for orchestrator classification)

Review/verify steps should declare `verdict_inputs` (the footprint classes their verdict depends on), so
a post-review HEAD advance re-fires only steps whose inputs the delta intersects — e.g. a one-line Java
change re-fires the quality gate and code review, not the security audit or simplify; a docs-only
delta re-fires none of the code reviews. Until then, an operator-side mitigation: batch late fixes
(Sonar + review advisories) into one commit before the loop-back rather than one per finding.

May already be tracked in plan-marshall (verdict_inputs reuse) — dedup before filing.
