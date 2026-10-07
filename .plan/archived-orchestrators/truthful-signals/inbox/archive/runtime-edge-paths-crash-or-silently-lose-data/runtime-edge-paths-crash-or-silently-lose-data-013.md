envelope_version=1
sender_type=plan
sender_id=runtime-edge-paths-crash-or-silently-lose-data
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T20:35:24Z

component=plan-marshall:automatic-review
category=anti-pattern
confidence=high
source_plan=runtime-edge-paths-crash-or-silently-lose-data
source_finding=61284d
source_signal=automated_review
likely_epic=review-apparatus

# The bot that reliably finds nothing is the one gating the quorum

## Context

On PR #1132 the participation predicate returned `participation_complete: true` with
`proves: participation_only`. The bot states behind that verdict:

| Bot | State | Required? |
|-----|-------|-----------|
| pr-agent | `participated_but_empty` | required |
| coderabbit | `refused_awaitable` | optional |
| sourcery | `refused_hard` | optional |

In substance **no reviewer produced a single actionable comment on this diff**. The required bot
published in a declared evidence shape but contributed no content; both optional bots refused for
rate-limit reasons.

## Why this is a recurrence, not an incident

This is the **third consecutive occurrence of the same shape**. The project memory records it on
#1122 and #1123, where the one required bot found nothing while coderabbit and sourcery found real
defects.

That is the asymmetry worth naming: **the bot that reliably finds nothing is the one gating the
quorum, and the two that reliably find real defects are optional.** A required/optional split whose
required member is the least productive reviewer converts the quorum from a review gate into an
attendance check.

## The recovery path existed and was configured off

`review_rate_window_await` was `false`, so coderabbit's awaitable window was **detected and then
not awaited**. The mechanism that would have converted a `refused_awaitable` into an actual review
was present and disabled. When the only substantive reviewers refuse for a reason that is by
construction temporary, declining to wait is the decision that turns a recoverable gap into a
permanent one.

## What the predicate got right

The predicate is scrupulous: it reports `proves: participation_only`, not `reviewed`. It is not
lying. The defect is that a downstream reader — including the merge barrier and the operator — sees
`participation_complete: true` and reads it as "review happened". The honest sub-field is dominated
by the confident headline, which is precisely this epic's subject.

## Proposed action

1. Re-weight the required/optional split against observed productivity: a bot whose last N reviews
   produced zero actionable comments should not by itself satisfy the quorum.
2. Make `participation_complete` carry its `proves` value into every consumer that renders it, so
   `participation_only` can never be displayed as an unqualified `true`.
3. Reconsider the default for `review_rate_window_await` when the refusing bots are the ones with a
   track record of finding defects — an awaitable refusal is a wait, not a verdict.
4. Add a distinct state for "every substantive reviewer refused" so it is separable from "reviewers
   reviewed and found nothing". Those two are currently indistinguishable at the gate.

## Evidence

- finding `61284d` (this plan), severity warning, component `plan-marshall:automatic-review`
- `automatic-review` step recorded `outcome: done`, `display_detail: "0 comment(s) found (unified triage pending)"`
- `project:finalize-step-review-retrospective` recorded `0 pr-comment findings - nothing to compare`
- prior occurrences: #1122, #1123

## Routing note

Review-bot subject matter — most likely belongs to the **`review-apparatus`** epic. Flagged as a
lead for the drain; the plan performs no epic classification.
