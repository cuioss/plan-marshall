envelope_version=1
sender_type=plan
sender_id=truth-166-architecture-refresh-migration-churn
epic=truthful-signals
kind=candidate-lesson
created=2026-09-17T02:35:34Z

component=plan-marshall:automatic-review
category=improvement
confidence=high
rank=9
source_plan=truth-166-architecture-refresh-migration-churn

# Measure self-seeding on the EXTERNAL review loop too, where a round costs a rate-limited hour

## Context

Message 006 measured self-seeding inside `pre-submission-self-review` (55% overall, 79%
after round 1) and proposed a deletion-only default plus a published self-seeded share as
that loop's stop signal. Its scope is the in-house loop; it cites the CodeRabbit defects
only as evidence that four in-house rounds missed them.

The same measurement on the EXTERNAL loop has not been taken, and it comes out worse.
Three CodeRabbit rounds ran on PR #1501, at commits `0f4ea46`, `36188c8` and `b7a6c23`.
Two of the three re-found residue of the immediately preceding remediation:

| Round | Commit | Actionable | Attributable to the previous round's fix |
|------:|--------|-----------:|------------------------------------------|
| 1 | `0f4ea46` | 6 | — (first round) |
| 2 | `36188c8` | 2 | 1 of 2 — `manage-api.md:15-16`, the sibling site TASK-12's fix did not sweep |
| 3 | `b7a6c23` | 1 | 1 of 1 — `0e04c9`, a vacuity inside the guard TASK-15 had just added |

Both are recorded in the run's own resolution details, unprompted: "yours is the sibling
site that sweep missed, which is also why it is in scope despite sitting outside the diff
hunks", and "this is a vacuity inside the guard that `b7a6c23ac` added to close a vacuity".

## Root cause

Two different misses, one shared shape — the remediation acted on the REPORTED site
instead of on the site population the claim spans:

- Round 2's miss: TASK-12 corrected the `derived.json`-as-live-layout claim where
  CodeRabbit reported it (`architecture-persistence.md` Storage) and did not enumerate the
  other places the same claim is stated. `manage-api.md:15-16` was one call away —
  `architecture search --content` over the claim would have returned it.
- Round 3's miss: TASK-15 added a doc-vs-source guard and the guard's own parse had a
  last-write-wins collapse, so the fix shipped without a control proving it reddens.

## Why this is not message 006 restated

The loop, the cost model, and therefore the remedy all differ:

- **Loop**: 006 governs `pre-submission-self-review`. This governs the PR-remediation
  response cycle in `automatic-review`.
- **Cost**: an in-house round costs a dispatch. An external round costs a **rate-limited
  hour** — every review body on this PR ends "Your plan provides up to 1 included review
  per hour; 0 remain after this review", and each trigger resets the window. Two avoidable
  external rounds is not two dispatches, it is two hours of wall clock on the critical
  path to merge, at the point in the plan where the merge gate is already waiting.
- **Remedy**: 006's deletion-only default does not reach this loop, because a
  PR-remediation fix is usually a correction rather than an addition. The move that closes
  BOTH misses here is different: before responding to a finding, **derive the population
  the finding's claim spans** (a content sweep for the claim; the sibling branches that
  reach the same state) and fix the population, not the line — and when the fix is itself
  a guard, land its matched control in the same commit.

## Proposed action

1. Add a remediation-scope step to the `automatic-review` response path: for any finding
   whose subject is a stated contract, claim, or branch rule, run one
   `architecture search --content` for that claim and respond over the returned set, with
   the returned `count` and coverage fields quoted in the response so the scope is visible
   and falsifiable.
2. Require any finding closed by ADDING a guard to land a matched positive/negative
   control in the same commit. Round 3's finding is exactly the case a control would have
   caught before the reviewer did.
3. Publish the per-round externally-attributable share the same way 006 asks for the
   in-house share, so the two loops are measured on one scale.

## Evidence

- `manage-findings list --type pr-comment --resolution fixed` — 9 records
  (7 actionable + 2 review bodies), `reviewed_commit_sha` spanning the three rounds above.
- `38b7c4` resolution detail — names the sibling-site miss and attributes it to TASK-12.
- `0e04c9` resolution detail — names the vacuity inside the round's own new guard.
- Every CodeRabbit review body on this PR — "up to 1 included review per hour; 0 remain".

## Generalizes

A remediation loop's self-seeding rate has to be measured per loop, because the currency
differs: a cheap dispatch tolerates rediscovery, a rate-limited external review does not.
Fixing the site a reviewer happened to point at, rather than the population the claim
spans, converts one report into two rounds — and the second round arrives an hour later,
against a merge gate that is already open.
