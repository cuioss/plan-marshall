envelope_version=1
sender_type=plan
sender_id=terminal-title-channel-reconciliation
epic=truthful-signals
kind=candidate-lesson
created=2026-07-27T19:55:18Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=anti-pattern
source_plan=terminal-title-channel-reconciliation
source_pr=1023
source_finding=ef45f5

# A fix for the archetype introduced the archetype — and a 250-candidate self-review passed it CLEAN

## Observation (first-party, PLAN-79 / PR #1023)

Deliverable **D3** existed for exactly one purpose: *make machine-set title-token state
machine-cleared, with **owner scoping*** — so a clearer only clears state it owns.

D3 shipped an **in-memory clear that was unconditional**, while its **persisted sibling was
owner-scoped**. The two halves of the same conceptual operation disagreed on the very
property the deliverable was created to establish. CodeRabbit caught it.

`pre-submission-self-review` ran on that same diff and reported
`self-review clean: 250 candidates examined`.

## Two distinct, separately reusable findings

### 1. The archetype survives its own fix (vacuous-guard family)

A deliverable whose *stated purpose* is "add scoping/guard X" is not evidence that X is
present everywhere it must be. The fix's author holds the property in mind while writing the
part they are thinking about, and the sibling path — the in-memory twin of a persisted
write, the cache twin of a store write, the fast path of a slow path — inherits the *old*
unscoped behaviour because it was never the subject of the change.

**Corrective rule:** when a change introduces a predicate/guard/scope to an operation,
enumerate **every implementation of that operation** (persisted + in-memory, sync + async,
fast-path + slow-path) and assert the predicate on each. A deliverable that adds a guard MUST
close with an explicit enumeration of the guarded set, not with "the guard was added".

This is now the **second** self-inflicted instance of the archetype (after `#1013`
`_split_bundle_version`, which PLAN-81 tracks). Two of the archetype's instances were
introduced by fixes *for* the archetype. That is a strong argument that the archetype is not
a discipline problem but a missing structural check.

### 2. `250 candidates examined` is a volume number, not a coverage number

The self-review's `display_detail` reports how many candidates its deterministic surfacers
produced. It reports nothing about whether the *defect class present in this diff* was among
the classes surfaced. On this diff it was not: a symmetric-pair divergence where one member
gained a guard and the other did not is precisely a `symmetric-pair-functions` /
`flag-guard-pairs` shape that the surfacer list nominally covers — yet the pass returned
CLEAN.

**Corrective rule:** a coverage-class gate MUST NOT report a candidate/volume count as its
headline verdict. Report which candidate classes fired and which returned empty, so an empty
result for a class that *should* have matched is visible. `CLEAN (250 examined)` and
`CLEAN (250 examined, symmetric-pair class returned 0 matches on a diff containing 2
symmetric pairs)` are the same verdict with completely different trustworthiness.

## Truthful-signals relevance

Both halves are the epic's theme in pure form. The deliverable's *name* asserted the property
it failed to establish; the self-review's *number* asserted a thoroughness it did not have.
Neither signal was false — D3 did add owner scoping (in one place), and the self-review did
examine 250 candidates. Both were read as claims they never made.
