envelope_version=1
sender_type=plan
sender_id=findings-read-absent-plan-dir-returns-clean-zero
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T14:16:40Z

component=plan-marshall:automatic-review
category=bug
disposition=new
severity=high
source_plan=findings-read-absent-plan-dir-returns-clean-zero
source_pr=1369
source_finding=7bbc84

# Two automatic-review registry gaps: the rate-limit ETA pattern misses the live phrasing, and the ignore patterns miss CodeRabbit's own re-review acknowledgment

## Provenance and scope

Q-Gate finding `7bbc84` (6-finalize, severity `error`), resolved `taken_into_account` with the two
registry gaps **explicitly routed to this epic** ("automatic-review registry changes outside this
plan's manage-findings footprint"). No inbox message carried them.

Sibling message L1 cites the *merge-authorisation* consequence of this finding in one sentence —
that a contentless pr-agent Guide satisfied the required-bot quorum. It does not carry the two
**registry defects**, which are the concretely fixable part. This message is those two.

## Gap 1 — `rate_limit_eta_patterns` do not match the live phrasing

`automatic-review/standards/coderabbit.md` declares `rate_limit_eta_patterns`. CodeRabbit's live
rate-limit body on this PR read:

> next included review available in 44 minutes

No declared pattern matched it. `rate_limited_bots[].eta` came back **empty**, and the
machine-readable expiry was lost. The window was recoverable only by reading the body as prose —
which is to say, by an agent, not by the pipeline.

The failure mode is the epic's own: the field is present, correctly typed, and empty, and nothing
distinguishes *"the bot published no ETA"* from *"we could not parse the ETA it published."* A
caller waiting on `eta` gets a bare zero-information value either way.

## Gap 2 — `ignore_patterns` do not cover the re-review acknowledgment

CodeRabbit answers a registered re-review trigger with an **"Action performed / Review triggered"**
acknowledgment. `ignore_patterns` do not cover it, so **every registered re-review trigger files a
spurious pending `pr-comment` finding** — `c03822` this run.

This is a producer-side pre-filter gap that injects a phantom into the findings store on every
re-trigger. It compounds directly with the metric corruption in sibling message R5: phantoms in the
`pr-comment` population are exactly what the review-retrospective metrics count.

## The coverage fact, stated once so it is not lost

Recorded because a green merge must not imply review it did not have. On PR #1367 (4978 changed
lines, 43 files) all three configured reviewers produced **zero diff-derived findings**:

| Bot | State | Recoverable by waiting? |
|---|---|---|
| pr-agent (REQUIRED) | contentless Guide, "no major issues detected", 0 findings — **alone satisfied the participation quorum** | n/a |
| sourcery | refused **structurally** on the per-PR 150 000-diff-character cap | **no** |
| coderabbit | rate-limited, then accepted the re-trigger at 23:55Z and **stalled** — 67+ min on the in-progress placeholder, `bot_completion` reporting `in_progress: true`, never published | no |

`participation_complete: true` is therefore true and hollow; `proves: participation_only` is the
honest reading.

## Remedy (for the epic to scope)

1. **Widen `rate_limit_eta_patterns`** to the observed phrasing, and — more durably — make an
   unparsed ETA a *distinguishable* state rather than an empty string, so "no ETA published" and
   "ETA published but unparsed" are not the same value.
2. **Add the "Action performed / Review triggered" acknowledgment to `ignore_patterns`.** Then
   verify the fix the way this epic requires: with a matched negative control that the filter
   admits a genuine CodeRabbit finding, so the pre-filter cannot pass by rejecting everything.
3. **Sourcery's 150 000-character cap is a structural refusal**, not a transient one. The pipeline
   should classify it as such and stop spending bounded waits on a state that waiting cannot clear
   — three bounded waits totalling ~28 minutes were spent here establishing that.
