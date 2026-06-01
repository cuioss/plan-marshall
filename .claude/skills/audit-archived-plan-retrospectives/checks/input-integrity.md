# Check: input-integrity (per-plan health + corpus data_confidence summary)

The **no-false-healthy FOUNDATION** for the whole audit. Every other check reads
a subset of a plan's structured inputs and reports the signals it derives from
them. If those inputs are absent or under-recorded, a peer check's "no findings"
verdict is a **FALSE HEALTHY** — the check saw nothing because there was nothing
to see, not because the plan was clean. This check makes that distinction
explicit and deterministic.

It is a **per-plan** check (one health row per scanned plan) that ALSO emits a
corpus `data_confidence` summary header. The deterministic computation lives in
`scripts/audit.py` (`check_input_integrity` / `emit_input_integrity_block`); this
sub-document is the interpretation guide and the source of the standing
cross-check obligation every other check owes this verdict.

## Inputs the check reads

The canonical per-plan input set — the artifacts the downstream checks depend on:

| Input | Path | Consumed by |
|-------|------|-------------|
| Execution manifest | `execution.toon` | execution-context-manifest |
| Per-phase metrics | `work/metrics.toon` | metrics, token-efficiency-trend, token-economics, global-log windows |
| References / footprint | `references.json` | scope-estimate-accuracy, task-count-efficiency, token-economics |
| Tasks | `tasks/TASK-*.json` | task-count-efficiency, token-economics |
| Findings | `artifacts/findings/*.jsonl` | quality-verification-report, recurring-pattern-detector, quality-chain |
| Script-execution log | `logs/script-execution.log` | sequence-and-build-minimality |
| Work log | `logs/work.log` | sequence-and-build-minimality phase attribution |

## Per-plan health columns

Presence/health booleans (`true` / `false`) for the canonical input set:

| Column | True when |
|--------|-----------|
| `has_execution` | `execution.toon` is present. |
| `has_metrics` | `work/metrics.toon` is present. |
| `has_references` | `references.json` is present. |
| `has_tasks` | `tasks/` exists with at least one `TASK-*.json`. |
| `has_findings` | `artifacts/findings/` exists with at least one `*.jsonl`. |
| `has_script_log` | `logs/script-execution.log` is present and non-empty. |

`has_findings` is the one OPTIONAL artifact: a clean plan may legitimately have
recorded zero findings, so an absent findings dir alone does NOT fire a flag or
escalate the `data_confidence` bucket. The other five inputs are expected on any
plan that ran a full lifecycle.

## The three flags

These are the input-health defects that silently FLOOR every downstream check:

| Flag | Fires when | Why it floors downstream checks |
|------|------------|---------------------------------|
| `metrics_blind` | Any data-bearing phase (`4-plan`, `5-execute`, `6-finalize`) recorded **zero** tokens. The cell lists the blind phase names (`;`-joined). | A zero-token phase means every token-economics and token-trend number for that phase is under-counted. The **5-execute** case is load-bearing — a blind execute escalates the plan to the `blind` data_confidence bucket. |
| `incomplete_lifecycle` | The plan never recorded a `5-execute` OR a `6-finalize` section in `metrics.toon`. The cell lists the missing phase names. | The plan did not run to completion through the recorded lifecycle, so completeness-dependent checks (pr-merge-velocity, quality-chain resolution) read a truncated history. |
| `missing_dispatch_markers` | `logs/work.log` carries no `[DISPATCH] role=phase-N` line. | The sequence-and-build-minimality phase attribution cannot bucket calls into phases — it folds everything into `1-init` (the finalize-fold conflation caveat in that check's sub-doc). |

## Corpus data_confidence summary

A three-bucket tally over the scanned plans, emitted as summary lines above the
per-plan rows:

| Bucket | A plan lands here when |
|--------|-----------------------|
| `fully-recorded` | No flag fired: every canonical input present, no blind phase, a complete lifecycle, and dispatch markers present. |
| `partial` | At least one input absent, or a non-execute zero-token phase / incomplete lifecycle / missing dispatch markers — **but the 5-execute phase DID record tokens** (not blind). |
| `blind` | The **5-execute** phase recorded zero tokens (`metrics_blind` on the load-bearing phase). Every downstream number for these plans is a FLOOR. |

The bucket precedence is `blind` > `partial` > `fully-recorded`: a blind execute
wins regardless of other inputs.

## Emitted columns

```
plans_scanned: N
data_confidence_fully_recorded: F
data_confidence_partial: P
data_confidence_blind: B
blind_plan_ids: "id1;id2"
genuine_signal_count: G
rows[N]{plan_id,has_execution,has_metrics,has_references,has_tasks,has_findings,has_script_log,metrics_blind,incomplete_lifecycle,missing_dispatch_markers,data_confidence,severity}
```

| Column | Meaning |
|--------|---------|
| `has_*` | The six presence/health booleans above. |
| `metrics_blind` | `;`-joined blind data-bearing phase names, or empty. |
| `incomplete_lifecycle` | `;`-joined missing lifecycle phase names (`5-execute` / `6-finalize`), or empty. |
| `missing_dispatch_markers` | `true` when no dispatch marker exists, else empty. |
| `data_confidence` | The per-plan bucket (`fully-recorded` / `partial` / `blind`). |
| `severity` | Uniform D1 severity column: `genuine` when any of the three flags fired, `informational` otherwise. |

`genuine_signal_count` counts the rows with a real input-health defect. A
`fully-recorded` plan, or a plan whose only gap is the optional findings file, is
`informational`.

## The cross-check obligation (standing rule for EVERY other check)

This check's verdict is the **deterministic foundation for no-false-healthy
enforcement**. Every other check MUST consume it:

1. **Annotate floored rows.** Any row a peer check derives from a plan this check
   marks `metrics_blind` (especially a `blind`-bucket plan) MUST be annotated
   **"floor, not truth"** in the adjudication. A token-economics or token-trend
   number computed over a blind execute is an under-count, not a measurement.
2. **No "all healthy" over blind-input plans.** A check MAY NOT conclude "all
   healthy" / "no findings" for the corpus while `data_confidence_blind > 0`. The
   blind plans' downstream rows are floors — absence of a signal there is absence
   of *recorded data*, not absence of a problem. The conclusion must instead read
   "no findings among fully-recorded plans; the N blind plans are floored and
   cannot be cleared".
3. **Name the blind plans.** When dismissing a blind plan's row as "no signal",
   the dismissal MUST cite this check's `blind_plan_ids` list as the reason the
   row cannot be cleared, not generalize it to a healthy verdict.

This obligation is mirrored in SKILL.md's Step 3 (per-row adjudication) and Step
4b (the review-completeness gate): the gate cannot truthfully reach "no findings"
while any plan is `blind` here.

## How the orchestrator interprets the rows

- **`data_confidence: blind`** — highest-priority structural signal. The plan's
  execute phase recorded zero tokens; every downstream token number for it is a
  floor. Do NOT clear any of the plan's peer-check rows as healthy. If the blind
  recording recurs across plans created after a metrics-recording fix shipped,
  that recurrence is the file-worthy signal (the recording defect itself), routed
  through the three-gate policy.
- **`metrics_blind` (non-execute phase)** — a `4-plan` or `6-finalize` zero-token
  recording. Flags the specific phase as under-counted; the plan stays `partial`
  (not `blind`) because the load-bearing execute phase still recorded data.
  Annotate the affected phase's downstream numbers as floored.
- **`incomplete_lifecycle`** — the plan stopped before recording execute or
  finalize. Cross-read with pr-merge-velocity (likely `applicable: false`) and
  quality-chain (truncated resolution history); do not read a missing PR as "no
  PR was needed".
- **`missing_dispatch_markers`** — the sequence-and-build-minimality phase graph
  for this plan folds into `1-init`. Read that check's per-phase attribution for
  the plan as unreliable (the finalize-fold conflation caveat).
- **`fully-recorded` / `informational`** — a clean input surface. The plan's peer
  rows can be read at face value. Still adjudicate each peer row on its own
  merits; a clean input surface clears the *floor*, not the *signals*.

Per the SKILL.md Step-3 contract, EVERY emitted row is adjudicated with a stated
verdict and cited evidence; a row may be dismissed as informational/expected ONLY
with a cited reason (the `severity: informational` cell, or the
`fully-recorded` bucket).

## Critical rules

- The script is the single source of truth for the input presence checks, the
  three flags, and the `data_confidence` bucketing. Do not re-stat the plan dirs
  or re-derive a flag in chat.
- The data-bearing phase set, the load-bearing execute phase, and the
  dispatch-marker grammar are module constants
  (`_II_DATA_BEARING_PHASES`, `_II_EXECUTE_PHASE`, `_II_DISPATCH_RE`). If the
  recorded lifecycle changes, edit `scripts/audit.py` rather than substituting a
  different reading.
- The cross-check obligation is NOT optional: a peer check that claims "all
  healthy" while this check reports a `blind` plan is producing a false healthy —
  the exact failure mode this check exists to block.
- This check is read-only; it never edits `.plan/` files.
