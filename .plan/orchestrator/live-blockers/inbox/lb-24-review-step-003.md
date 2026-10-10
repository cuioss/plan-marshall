envelope_version=1
sender_type=plan
sender_id=lb-24-review-step
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T11:57:46Z

component=plan-marshall:automatic-review
category=bug

# Treat CodeRabbit's full-review acknowledgment and its in-place edit as noise

## Context

On PR #1742 CodeRabbit answered `@coderabbitai full review` with an issue comment reading "Action performed / Full review triggered.", later edited in place to "Full review finished.". `fetch_findings` stored the first version as finding 5d2262 and, because the edit changed the edit term, the second version as finding 74f32d. Both reached the unified triage as pending review comments and were closed `taken_into_account` by hand. Deliverable 4 of this same plan added acknowledgment patterns for exactly this class.

## Root cause

The registry's `acknowledgment_patterns` hold "Review triggered" and "Review finished", matched as case-sensitive substrings. The reply to the escalated command reads "Full review triggered." / "Full review finished.", which does not contain either literal with that capitalisation. The wording was never observed live; the self-review flagged it as an unexercised branch (coderabbit.md:68).

## Proposed action

Match the acknowledgment literals case-insensitively (or add the "Full review ..." forms) and drop an edited acknowledgment as the same comment, not a new finding. Add a fixture with the observed bodies from PR #1742.

## Evidence

- automatic-review hand-back at e2b8d0b45: acknowledgment filed twice (5d2262, 74f32d)
- decision.log 2026-10-09T23:54:38Z: triage resolved both as acknowledgment noise
- review-retrospective: 'Full review triggered/finished' slipped past the acknowledgment filter
