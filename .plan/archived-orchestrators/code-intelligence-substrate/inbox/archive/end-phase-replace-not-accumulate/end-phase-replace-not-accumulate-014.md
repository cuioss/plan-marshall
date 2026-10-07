envelope_version=1
sender_type=plan
sender_id=end-phase-replace-not-accumulate
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T17:25:44Z

component=plan-marshall:plan-retrospective
category=improvement
created=2026-07-29

# Three structural defects in the retrospective's own machinery: a check that cannot fire, a section with no producer, and an aspect with three names

Observed live while running the retrospective on this plan. All three are in the component that grades other components.

## 1. The shape_violation check is vacuous

`standards/execution-context-dispatch-audit.md` defines `shape_violation` as a resolve-without-dispatch pairing: a `decision.log` `(plan-marshall:manage-config)` `effort resolve-target` entry with no subsequent `[DISPATCH]` line for the same role.

This plan's `decision.log` contains **zero** `effort resolve-target` entries, across **17** dispatches. Surface B is empty, so the pairing has no left-hand side and the check cannot produce a finding under any circumstances. Its reported `shape_violation: 0` means "never evaluated", not "evaluated clean" — the same floor-not-truth distinction `manage-metrics generate` already makes explicit for unrecorded phases, absent here.

Either the resolver is expected to log and does not, or the audit is built on an evidence surface that no producer writes. Either way the check has never been able to fire.

## 2. "Phase Dispatch Boundaries" is a producerless report section

`compile-report` returned:

```
sections_omitted[1]:
  - Phase Dispatch Boundaries
```

`dispatch_boundaries` is a valid registry key in `collect-fragments`, but **no row of the SKILL.md aspect table produces it** — the boundary data is emitted inside `analyze-logs`' own fragment under a nested `dispatch_boundaries:` block. So the section is omitted on every run, forever, and the omission is classified BENIGN ("the section's trigger fragment was absent... there was nothing to lose") when in fact the data exists and was rendered elsewhere.

The same run's Executive Summary rendered `_No executive summary provided._` — likewise no aspect produces it. Two sections of the report template have no producer.

## 3. One aspect, three names

The invariant aspect is called:

- **"Invariant outcomes"** — SKILL.md Step 3 aspect table, row 3
- **`invariant-check-summary.md`** — the reference file the same row points at
- **`invariant-summary`** — the only key `collect-fragments add` accepts

Registering by the documented label failed live in this run:

```
error: Unregistered aspect key: 'invariant-outcomes'. ... so compile-report would silently drop its section
```

The error message is good — it names the valid set and states the consequence. But the SKILL that instructs the caller uses a label that is not in that set, so the trap is authored into the workflow the caller is told to follow.

## Impact

A retrospective whose own checks include one that cannot fire, whose report has two permanently-empty sections classified as benign omissions, and whose aspect table names a key the registry rejects, is weaker evidence than its clean `status: success` suggests. The `sections_dropped[0]` all-clear this run reported is accurate as far as it goes, and it does not cover any of the three.

## Suggested corrective action

1. Decide whether `effort resolve-target` should log to `decision.log`. If yes, add the emission and the check becomes real. If no, replace `shape_violation` with a check keyed on a surface that exists, and until then have the audit report `shape_violation: not_evaluated` (with the empty-population reason) instead of `0`.
2. Either give `dispatch_boundaries` a producing aspect row, or remove the section from the report template and the key from the registry. Same for Executive Summary — either an aspect synthesizes it or the heading goes. Distinguish "no producer exists" from "producer ran and found nothing" in `sections_omitted`, since only the latter is genuinely benign.
3. Rename to one canonical `invariant-summary` across SKILL.md's table label and the reference filename, so the documented name, the file name, and the registry key agree.
