envelope_version=1
sender_type=plan
sender_id=the-ledger-has-no-safe-single-row-append
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T08:07:19Z

component=plan-marshall:automatic-review
category=bug
confidence=high

# Match the live "Next included review available in N minutes" rate-limit ETA

## Context

Every rate-limit notice CodeRabbit posted during this run stated its own reset time in the form "Review limit reached - Next included review available in 57 minutes". The run read all six ETAs (57, 44, 27, 50, 2, 45 minutes) by hand out of the comment bodies, because the producer reported no ETA.

`automatic-review/standards/coderabbit.md` declares exactly three `rate_limit_eta_patterns`:

- `wait ([0-9]+ minutes? and [0-9]+ seconds?) before requesting another review`
- `wait ([0-9]+ (?:minutes?|seconds?|hours?)) before requesting another review`
- `([0-9]+ (?:minutes?|hours?)) before (?:the )?(?:rate )?limit resets`

None of the three matches the live wording. There is no "wait ... before requesting" and no "before the limit resets" in the notice actually posted.

## Root cause

Two failures compound. The extraction patterns have drifted from the live notice wording. And the contract then instructs the caller to read the resulting empty value as a statement about the NOTICE rather than about the PATTERNS: coderabbit.md states "A notice that states no ETA simply yields an empty `eta`, which the caller reports as unknown". So `eta: ""` conflates "the notice stated no ETA" with "the notice stated one and no pattern matched" - the confident-signal-hides-a-caveat shape.

## Proposed action

Add a pattern matching `Next included review available in ([0-9]+ (?:minutes?|hours?))`. Separately, and more durably, distinguish the two zeros: emit a marker saying whether any rate-limit notice text was present at all, so an empty `eta` beside a present notice is legible as an extraction miss rather than as an absent ETA.

## Evidence

- marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md lines 75-78 — the three declared patterns, verified against HEAD.
- decision.log 2026-09-06T09:38:22Z — the live notice: "'Review limit reached' plus 'Next included review available in 57 minutes'".
- decision.log 2026-09-06T16:59:46Z — six hand-read ETAs across the run.
- coderabbit.md lines 209-210 — the contract sentence that turns an unmatched pattern into an apparent absent-ETA.
