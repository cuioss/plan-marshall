envelope_version=1
sender_type=orchestrator
sender_id=test-quality
epic=process-compliance
kind=finding
created=2026-09-20T20:54:23Z

# Addendum 2: Sourcery reviews despite skip-bot-review (PLAN-140 run 3)

Operator instruction: `skip-bot-review` suppresses CodeRabbit only. Sourcery may still review when not rate-limited. Handling rule: every labelled PR is still checked for Sourcery review comments; any comment present is triaged and handled exactly as on an unlabelled PR (fetch findings, disposition, respond/post, re-verify), even though the label theoretically suppressed review.

Application to run 3 (B0 mechanical + B1–B4):
- After opening each PR (labelled or not), poll for Sourcery findings within the normal review window before merging.
- A labelled PR with zero Sourcery comments merges on the 5 machine facts. A labelled PR WITH Sourcery comments does not merge until each comment is triaged/handled — the label never justifies ignoring a review that actually arrived.
- Record per-PR in D5: label applied (y/n), CodeRabbit skipped (y/n), Sourcery present (y/n) + disposition of each finding.
