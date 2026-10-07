envelope_version=1
sender_type=plan
sender_id=correct-review-scores-as-maximally-wrong
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T13:00:30Z

component=plan-marshall:phase-6-finalize
category=bug
bundle=plan-marshall

# A leaf that returns a finding in its TOON but never persists it has reported nothing

## What happened

`pre-submission-self-review` pass 3 found a genuine defect and **returned it in its TOON** to the
caller. It never persisted it to the qgate store.

The finding therefore existed only in the dispatched leaf's return payload — in transcript, not in
state. Nothing downstream that reads the findings store (the blocking-findings gate, triage, the
finalize summary, any later retrospective) could see it. It survived only because a human read the
returned TOON in the moment.

## Why this is the dangerous shape

The return-value path and the persistence path are **independent**, and only one of them is
durable. A leaf can be fully successful by its own contract — correct analysis, correct TOON,
`status: success` — while contributing **zero** to the state the pipeline actually gates on.

The failure is silent in both directions:

- Nothing errors, so no gate trips.
- The finding *appears* reported, because the caller can see it. The gap is invisible precisely at
  the moment someone is looking at the evidence.

This is a sibling of the unchecked-persist archetype (a persist that is called but whose result is
never read). Here the persist is not even attempted, and the TOON return creates a false
impression that it was.

## Rule

- **A dispatched leaf's TOON return is a *summary of* persisted state, never a substitute for it.**
  Any finding a leaf reports MUST be written through `manage-findings` (per-plan or qgate) before
  the leaf returns; the TOON then reports counts/ids of what was persisted.
- **Report a persisted identifier, not a description.** When a leaf's return carries a `hash_id`
  from the store rather than free prose, an unpersisted finding becomes structurally
  unrepresentable in the return payload.
- **Cross-check counts at the dispatch boundary.** The caller should be able to compare the leaf's
  claimed finding count against a store read for that phase; a mismatch is the detector for this
  whole class. A leaf claiming N findings with 0 in the store is the exact signature.
- Applies to every self-review / verification leaf that emits findings, not only to
  `pre-submission-self-review`.

## Status

Observed first-hand during `correct-review-scores-as-maximally-wrong` (PR #1078). **Not fixed** by
that PR — filed for the epic as a live gap in the finding-persistence path.
