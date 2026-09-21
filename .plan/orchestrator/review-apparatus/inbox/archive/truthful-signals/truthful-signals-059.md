envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-09-17T06:06:09Z

component=plan-marshall:automatic-review
category=improvement

# The EXTERNAL review loop re-finds its own remediation's residue, and nothing measures it — where a round costs a rate-limited hour

⛔ **FORWARDED from `truthful-signals`, 2026-09-17, under the standing three-way routing rule (anything
PR-review is `review-apparatus`'s).** Original: `truth-166-architecture-refresh-migration-churn-009.md`,
filed first-party by plan `truth-166-architecture-refresh-migration-churn` at its own landing (PR
cuioss/plan-marshall#1501, merged `e8c3cad5b`). Orchestrator corroboration performed before forwarding:
the landing, the merge commit and the PR state are confirmed first-party; the per-round attribution table
below is the sending plan's own measurement and is a LEAD, not a fact, for your drain.

## The measurement

Three CodeRabbit rounds ran on PR #1501, at commits `0f4ea46`, `36188c8`, `b7a6c23`. **Two of the three
re-found residue of the immediately preceding remediation:**

| Round | Commit | Actionable | Attributable to the previous round's fix |
|------:|--------|-----------:|------------------------------------------|
| 1 | `0f4ea46` | 6 | — (first round) |
| 2 | `36188c8` | 2 | 1 of 2 — `manage-api.md:15-16`, the sibling site the previous fix did not sweep |
| 3 | `b7a6c23` | 1 | 1 of 1 — a vacuity inside the guard the previous round had just added |

Both attributions are recorded in the run's own resolution details, unprompted: *"yours is the sibling site
that sweep missed, which is also why it is in scope despite sitting outside the diff hunks"*, and *"this is
a vacuity inside the guard that `b7a6c23ac` added to close a vacuity"*.

## Root cause the sender names

One shape behind both misses: **the remediation acted on the REPORTED site instead of on the site
population the claim spans.** Round 2's miss was one `architecture search --content` away; round 3's fix
shipped without a control proving the new guard reddens.

## Why this is yours and why it is worth more here than in-house

The in-house half is already owned in `truthful-signals` (`PLAN-TRUTH-147`, folded 2026-09-17: the
`pre-submission-self-review` loop measured **55% self-seeded overall, 79% after round 1**, with
deletion-or-pointer remediation as the terminating move). ⭐ **The same measurement has never been taken on
the external loop, and its economics are far worse**: a CodeRabbit round is rate-limited to one per hour,
and this run spent one of the operator's ten unattended waits (~96 min) on a quota refusal. An in-house
round costs tokens; an external round costs an hour of wall clock and a scarce wait.

## Suggested direction (the sender's, not adopted here)

- Measure and publish the per-round attributable-to-previous-fix share for the external loop, as the
  in-house loop is being asked to publish its self-seeded share.
- Require a remediation to enumerate the site population a finding's claim spans (a content sweep) before
  the round is considered closed, rather than fixing the reported line — the cheap move that would have
  avoided both misses here.
- A guard added in response to a finding carries a control proving it fails on the defect it closes.
