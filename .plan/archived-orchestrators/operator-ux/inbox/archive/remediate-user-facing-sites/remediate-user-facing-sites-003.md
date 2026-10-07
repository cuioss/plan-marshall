envelope_version=1
sender_type=plan
sender_id=remediate-user-facing-sites
epic=operator-ux
kind=candidate-lesson
created=2026-09-08T12:40:37Z

component=plan-marshall:automatic-review
category=bug
confidence=high
source_plan=remediate-user-facing-sites

# Scope review-producer refusals by invocation so a spent rate-limit stops re-asserting

## Context

The review producer's `refusals[]` array carries no time scope and no invocation scope. A refusal
recorded once — here, a CodeRabbit rate-limit notice — keeps appearing in every subsequent poll's
output, long after the quota window it described has been waited out and the review has completed.

On this plan `automatic-review` fired 5 times. Each firing had to decide whether the refusal it was
looking at was live or already served, and the only way to tell was to compare the refusal's
invocation id against the current one. That distinction was made correctly, but it was made by
reading a field that happens to differ rather than by the producer saying which refusals are current.

The failure mode this narrowly avoided is expensive: reading a spent rate-limit refusal as live
starts a second 90-minute quota wait for nothing. The operator's recorded stall-recovery policy
already commits to waiting 90 minutes up to ten times, so a mis-read here compounds directly into
hours.

## Root cause

`refusals[]` is an accumulating record with no notion of currency. The consumer is left to infer
liveness from a field the producer never promised would carry that meaning.

## Proposed action

Stamp each `refusals[]` row with the invocation id and observation timestamp that produced it, and
have the reader drop every row whose invocation is not the current poll's. Equivalently: publish
`refusals_current[]` alongside the accumulating `refusals[]`, so the consumer reads currency off the
payload instead of deriving it. Either shape removes the inference; the accumulating array stays as
the audit trail.

## Evidence

- aspect: llm_to_script_opportunities — logged as candidate 2, complexity low, repetition 5.
- aspect: log_analysis — `automatic-review` recorded `firing_count: 5` with one `loop_back`;
  `status.metadata.coderabbit_quota_wait_count: 1`, so exactly one quota wait was genuinely owed
  and the refusal re-asserted on every poll after it.
