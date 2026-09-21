envelope_version=1
sender_type=plan
sender_id=self-review-resweeps-full-surface-every-round
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-09T03:23:29Z

component=plan-marshall:automatic-review
category=bug
bundle=plan-marshall
confidence=high
source_plan=self-review-resweeps-full-surface-every-round
route_hint=review-apparatus
source_aspects=chat-history-analysis,request-result-alignment

# A diff-size cap is not a rate limit - Sourcery refused PR 1126 on 150000 characters and waiting cannot clear it

Review coverage on PR #1126 was **1 of 3 bots**, with three distinct outcomes that the current handling collapses into one "bot did not participate" class:

| Bot | Outcome | Correct remedy |
|-----|---------|----------------|
| pr-agent | Participated; 2 focus areas, **both refuted** | none — see below |
| CodeRabbit | **Genuine rate limit**, never awaited | wait for the rate window, or claim it |
| Sourcery | **Refused on a DIFF-SIZE cap of 150,000 characters** | split the PR, or accept the gap — **waiting achieves nothing** |

The step's config carried `review_rate_window_await: false` and `review_rate_window_timeout_seconds: 3600`, i.e. the machinery it *has* is a rate-window one. There is no size-cap concept, so a size refusal is either silently bucketed with the rate refusal or reported as an unexplained non-participation.

## Root cause

Two failure modes with disjoint remedies share one representation. A rate limit is a *temporal* refusal (the same request succeeds later); a size cap is a *structural* refusal (the same request never succeeds). Any handling that offers "wait / accept the gap" as the option pair is offering a non-option on the size branch.

## Solution

Give the size cap its own taxonomy member, with its own remedy set (split / accept / disable-for-this-PR), and record the cap value in the finding so the gap is auditable against the actual diff size. Do not offer an await on a size refusal.

## Impact

**Effective external review value on this PR was zero.** The one bot that ran raised two focus areas, and both were refuted against live code:

- The "Scoping Bug" rested on a premise the target's own typed two-state contract contradicts (`_resolve_footprint -> list[str]`, where `[]` IS the unresolvable signal). Its suggested guard would have been **vacuous — an unreachable `else` branch** — and its only reachable effect would have made `allow_set` an empty set on a git error, turning a documented fail-safe into a fail-quiet clean verdict. Applying it would have introduced the exact defect class the plan existed to close.
- The "Unhandled Exception" area named `FileNotFoundError` and `OSError` (already handled by an `except OSError` in the read primitive) and `YAMLError` (impossible — there is no YAML library anywhere in that read path).

So on a PR where two of three reviewers structurally could not look, the third produced two findings that a careful reader had to spend real effort refuting. A green `automatic-review` step on this PR carries no evidence that anything was reviewed.
