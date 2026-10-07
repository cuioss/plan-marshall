envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:57:26Z

component=plan-marshall:plan-marshall
category=bug
title=Script-failure cluster 5/6 — phase_handshake reported drift twice, both times because a finding count fell rather than rose
confidence=high
source_plan=a-rule-that-is-green-because-it-examined-nothing
source_signal=script-failure cluster, notation plan-marshall:plan-marshall:phase_handshake

# Script-failure cluster 5/6 — phase_handshake reported drift twice, both times because a finding count fell rather than rose

## Observation

Two exit-1 `script_internal_failure` records, same notation, at consecutive phase boundaries:

```text
2026-08-08T13:20:11Z  phase=3-outline  drift_count=2
  qgate_open_count               captured "2"  observed "0"
  pending_findings_blocking_count captured "3"  observed "1"

2026-08-08T13:36:55Z  phase=4-plan     drift_count=1
  pending_findings_blocking_count captured "1"  observed "0"
```

Both are the **same direction**: the captured invariant recorded N open/blocking findings, and by the time the handshake verified, the plan had *resolved* them. The observed value is lower than the captured value in every one of the three diffs.

## Root cause

The handshake captures an invariant snapshot at one point and verifies equality at another. Q-Gate findings are resolved *between* those points — which is the intended workflow, not a fault. Equality is therefore the wrong predicate for a monotone-decreasing quantity: **resolving findings, the desired behaviour, is reported as drift.**

The consequence is a signal that costs attention on every phase boundary where the plan did the right thing, and — more importantly for this epic — **teaches the reader to discount `phase_handshake` drift**. A guard that fires on correct behaviour is a guard whose real firings will be waved through.

## Proposed action

- Make the predicate **direction-aware** for count invariants: a decrease in `qgate_open_count` / `pending_findings_blocking_count` is expected progress and should verify clean (or emit an informational note); only an *increase*, or a change in a non-monotone invariant, is drift.
- If the captured/observed pair must stay equality-checked, re-capture the snapshot after the resolution step rather than before it — the drift here is an artefact of snapshot placement, not of plan state.
- Either way, distinguish "drift" from "progress" in the emitted TOON so the two are not the same word.

## Why this belongs to `truthful-signals`

Inverted form of the epic's theme: not a green that hides a problem, but a **red that hides a success**. Both erode the signal's information content, and this one erodes it faster because it fires on the happy path.

## Evidence

- Work log entries `093bc2` (13:20:11, phase 3-outline) and `7b34eb` (13:36:55, phase 4-plan).
- Union-deduped by notation: 2 occurrences, 1 cluster.
- Neither occurrence blocked the plan; both were `override: false` and the phase advanced regardless — which is itself the reason the defect survives.
