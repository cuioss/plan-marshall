envelope_version=1
sender_type=plan
sender_id=lb-23-verify-builds
epic=live-blockers
kind=candidate-lesson
created=2026-10-09T10:02:01Z

component=plan-marshall:plan-marshall
category=improvement
created=2026-10-09
bundle=plan-marshall
source_plan=lb-23-verify-builds
confidence=high

# Let triage resolve a refuted PR comment as rejected, not taken_into_account

## Context

On plan lb-23-verify-builds CodeRabbit finding `944da6` (round 3, `canonical_verify.md:79`) claimed that no phase-5 code enforces the `build-decision` footprint guard. The triage leaf showed the guard is instructed in `phase-5-execute/SKILL.md` (the bot's own search had excluded every `.md` file) and replied "Declined as a false positive", but recorded the finding `taken_into_account`. The review-retrospective step then reported 0 false positives for CodeRabbit and flagged the record as a mis-triage it had no step to correct.

## Root cause

`plan-marshall/workflow/triage.md` Step 4 lists `fixed`, `suppressed`, `accepted` and `taken_into_account` as the triage resolutions and reserves `rejected` for the verify pre-stage. For `pr-comment` findings the producer declares no verification profile, so the verify pre-stage never runs and a refuted review comment has no path to `rejected`.

## Proposed action

- Allow triage to resolve a finding `rejected` when its own analysis refutes the claim, or run the verify pre-stage for `pr-comment` findings.
- Until then, have the review-retrospective aggregator read a "declined as a false positive" disposition from `resolution_detail` instead of counting only the `rejected` resolution, so reviewer precision is not overstated.

## Evidence

- aspect: chat_history_analysis - triage round 3: "taken_into_account instead of rejected for 944da6. triage.md Step 4 lists fixed / suppressed / accepted / taken_into_account as the triage resolutions, and rejected is reserved for the verify pre-stage, which did not run here".
- review-retrospective hand-back: "It belongs on rejected. I did not re-resolve it; the workflow has no step for that. The aggregator's count of 0 false positives stands as emitted".
- Reviewer table for this PR: coderabbitai 11 raw, 7 actionable, 6 fixed, 0 rejected.
