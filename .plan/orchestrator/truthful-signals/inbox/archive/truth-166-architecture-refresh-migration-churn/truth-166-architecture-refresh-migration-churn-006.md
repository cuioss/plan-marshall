envelope_version=1
sender_type=plan
sender_id=truth-166-architecture-refresh-migration-churn
epic=truthful-signals
kind=candidate-lesson
created=2026-09-17T02:29:28Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=high
rank=6
source_plan=truth-166-architecture-refresh-migration-churn

# Default the self-review loop to deletion-only remediation from round 2 onward

## Context

`pre-submission-self-review` fired 7 times on this plan: 3 loop-back rounds, a 4th
non-clean round closed by explicit operator decision, and 3 terminal firings. It filed 20
substantive Q-Gate findings (plus 2 `further_round_owed` bookkeeping markers), all fixed.

Self-seeding by round, measured from the findings and their resolution details:

| Round | Findings | Self-seeded | Share |
|-------|---------:|------------:|------:|
| 1 | 6 | 0 | 0% |
| 2 | 7 | 7 | 100% |
| 3 | 6 | 3 | 50% |
| 4 | 1 | 1 | 100% |
| **Total** | **20** | **11** | **55%** |

After round 1 the share is **11 of 14 (79%)**. Round 2's own marker states it outright:
"the round returned 7 findings in 2 classes, all in prose the round-1 fix authored", and
5 of the 7 finding bodies name the round-1 fix explicitly ("both were authored by the
same round-1 fix", "round 1 narrowed C and added K", "Branches J and K were added by the
round-1 fix").

## Root cause

Round 1's fixes closed findings by ADDING explanatory prose — new branches J and K, a
"carries only" field enumeration, a two-dimensions rationale paragraph. Every one of those
additions became a new contract-drift or duplicate-prose surface for round 2 to find. The
loop was generating its own backlog faster than it drained it.

## Proposed action

Two changes, both cheap:

1. Make **deletion-or-pointer** the DEFAULT remediation posture from round 2 onward,
   rather than a move a round discovers for itself. Round 2 adopted it explicitly ("all 7
   findings closed by deletion or pointer, no new explanatory prose added") and the
   self-seeded share then fell 100% → 50% → a single finding.
2. **Publish the per-round self-seeded share** as the loop's termination signal instead of
   re-deriving it as judgement each round. This is mechanical: join each pending finding's
   `file_path` against the commits that resolved earlier findings in the same phase.

## Evidence

- The terminating fixes are all deletions and pointers: "convergent fix is DELETION";
  "Deleted the Step 5 two-dimensions paragraph outright"; "Deleted the restatement in
  menu-pins.md Step 3 ... in favour of a pointer"; "the range is replaced by the selector
  that owns the set"; "the count is replaced by 'every epic-scoped verb' ... so the claim
  carries no number to go stale"; "removing three staleness sites rather than adding a
  fourth item to each".
- Four in-house rounds, a clean whole-tree `plugin-doctor` (37 rules, 0 issues) and a
  green `verify` still missed 7 actionable CodeRabbit defects — including `0e04c9`, a
  vacuity INSIDE the guard the previous round's fix had just added to close a vacuity.

## Adds to the known archetype

The pointer-not-restatement remedy is already known. What is new here is the measurement
(79% post-round-1, against 27% recorded on an earlier plan), the evidence that adopting
the remedy mid-loop demonstrably converged it, and the concrete proposal to make it the
default from round 2 with the self-seeded share published as the stop signal — so the
loop stops rediscovering the remedy one round at a time.
