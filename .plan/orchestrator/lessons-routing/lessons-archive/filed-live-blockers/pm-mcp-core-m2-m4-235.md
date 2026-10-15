envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T17:39:55Z

# Candidate lesson: Sourcery review-budget notice not recognised as a quota refusal by automatic-review

**Source plan:** plan-21-entity-addressing (PR #54)
**Signal source:** orchestrator-observed event, verified in work.log (5abcc8) and decision.log (ee2939, 090f75, 63b1d8, c61334)
**Suggested component:** plan-marshall:automatic-review (standards/sourcery.md refusal_patterns)

## What happened

- On the trigger-B re-review of head c846007, Sourcery answered with its notice that it had "used its review budget of N diff characters" (7-day budget).
- automatic-review did not match this text against the Sourcery refusal_patterns, so it treated the reply as an ordinary comment that does not reference the head SHA and recorded the re-review as **declined** (head_sha_verified=false), then escalated re_review_timeout to the operator as "re-review DECLINED by sourcery ... no budget expired".
- The notice was also filed as a pr-comment finding (1aa398, later dac92a) that triage had to accept by hand as informational.
- Only on the later round (14:30) was the state correctly described as "7-day review budget exhausted".

## Gap

The budget-exhaustion notice is a quota refusal, not a decline, but refusal_patterns in automatic-review/standards/sourcery.md does not cover its wording. The operator was given a wrong reason ("declined, no budget expired") for the escalation, and the notice was filed as a finding.

## Possible corrective action

Add the Sourcery review-budget wording ("used its review budget", "review budget of ... diff characters") to the Sourcery refusal_patterns so the re-review is classified as a quota refusal (not re-triggerable until the budget resets), the escalation names the right reason, and the notice is not filed as an ordinary pr-comment finding.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-21-entity-addressing-002.md` from plan plan-21-entity-addressing (PLAN-21, #54; Claude Code)
