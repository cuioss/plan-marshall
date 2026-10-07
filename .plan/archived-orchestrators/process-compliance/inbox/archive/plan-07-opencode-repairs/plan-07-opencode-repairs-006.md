envelope_version=1
sender_type=plan
sender_id=plan-07-opencode-repairs
epic=process-compliance
kind=candidate-lesson
created=2026-09-21T01:24:27Z

id=pending-orchestrator-pickup
component=plan-marshall:phase-6-finalize
category=improvement
created=2026-09-21

# Review-bot inline suggestions declined as contradicting plan intent

Automatic-review surfaced 3 comments on PR #1554 (2 inline by coderabbitai plus review_body summary). Both inline suggestions were triaged taken_into_account with Declined dispositions: f21a18 wiring format_unattended_consent_prompt into manage-status.py contradicts TASK-003 pure-rendering intent, bdb7ab reserving NO_SESSION_IDENTITY sentinel in every producer exceeds TASK-002 ADR-015 scope. Review_body 57052a carried no independent defect.

## Solution

Decline with plan-intent-contradiction rationale, citing covering tests and docs (test_merge_consent_prompt.py, sentinel contract docs and has_session_identity guard). No code change.

## Impact

Bot suggestions that expand scope beyond the tasked deliverables should be declined with explicit intent linkage rather than applied. Pattern for future triage: check TASK intent and ADR settlement before accepting cross-cutting bot refactors.

## Source

pr-comment findings f21a18, bdb7ab, 57052a on PR #1554, automatic-review step outcome done with 3 comments found. Candidate for orchestrator-side classification.
