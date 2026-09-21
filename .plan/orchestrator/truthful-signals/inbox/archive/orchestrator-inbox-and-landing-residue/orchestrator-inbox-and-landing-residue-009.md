envelope_version=1
sender_type=plan
sender_id=orchestrator-inbox-and-landing-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T17:01:43Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=orchestrator-inbox-and-landing-residue
source_aspects=signal_gate_inputs

# `signal_qgate_pending_count` does not carry a pending count, and the name made a careful reader file a false bug

## Context

`phase-6-finalize/SKILL.md` Step 3 item 4b evaluates a three-signal Signal Gate and forwards the three
counts to `lessons-capture` as bare integers on the prompt body. This run forwarded
`signal_qgate_pending_count: 19`.

The field name says *pending*. The contract's definition, in the same document, says otherwise:

> `signal_1_count = pending_subtotal + resolved_subtotal`, so Signal 1 fires on EITHER pending OR
> resolved-in-run Q-Gate findings

`resolved_subtotal` sums four resolutions — `fixed`, `suppressed`, `accepted`, `taken_into_account` —
across the five phases. `rejected` is deliberately outside that set.

Measured on this run, the forwarded value reproduces **exactly**:

| Phase | total | pending | rejected | counted (total − rejected) |
|-------|------:|--------:|---------:|---------------------------:|
| 2-refine | 1 | 0 | 0 | 1 |
| 3-outline | 6 | 0 | 1 | 5 |
| 4-plan | 0 | 0 | 0 | 0 |
| 5-execute | 2 | 0 | 0 | 2 |
| 6-finalize | 12 | 0 | 1 | 11 |
| **Total** | **21** | **0** | **2** | **19** |

0 pending + 19 resolved-in-run = **19**. The gate was correct.

## The defect, and the harm it actually caused

The defect is not the count — it is that a field named `..._pending_count` carries
*pending-plus-four-resolutions*, and the name is the only thing a consumer sees.

This is not hypothetical. The `lessons-capture` body that received this value read the field by its
name, computed pending-only (0 across all five phases), observed that nine of the twenty-one findings
were resolved on 2026-08-23 — a day before the gate fired — and concluded that the pending population
on 2026-08-24 could not have exceeded the twelve findings of `6-finalize`. From `19 > 12` it reported
the value as *above its own arithmetic ceiling*, i.e. not merely stale but impossible.

It then reached for an explanation and found a coincidence that fit perfectly: the logging-gap aspect
for this same run reports `context_load_attribution: total_rows: 19` — nineteen dispatch-boundary rows.
It hypothesised that the gate was querying the dispatch ledger rather than the Q-Gate store, "the same
number arriving at the wrong field."

Two 19s in one run, one of them a genuine coincidence, and a name that licensed the wrong reading. The
original version of this message carried that hypothesis and recommended confirming it before designing
a fix. Had it drained, the epic would have spent a plan chasing a cross-store bug that does not exist.

⭐ The reader did everything right — measured rather than assumed, stated the hypothesis as unverified,
named the caveat about `qgate clear`. Careful method did not save it, because the name is wrong at the
source and the body is forbidden from re-deriving the value that would have exposed it.

## Root cause

Three things compound, in order of leverage:

1. **Name/semantics divergence.** The field asserts a narrower quantity than it carries. Every consumer
   that trusts the name gets a wrong model, and the two readings differ most exactly when the gate is
   most interesting — a run that resolved many findings and left none pending, which is the healthy case.
2. **The verdict travels without its derivation.** The prompt body carries three bare integers: no
   per-phase breakdown, no resolution-set echo, no evaluation timestamp. Nothing in the payload could
   have distinguished the correct reading from the incorrect one.
3. **The one consumer positioned to notice is instructed not to look.** The workflow body is explicitly
   forbidden from re-deriving the counts, so the check that would have resolved the ambiguity in one
   query is ruled out by contract.

Note the failure direction is *open*, not closed: because the value is larger than a pending-only
reading, the gate dispatches an envelope rather than skipping one. Nothing breaks loudly; a reader
simply forms a false belief and files it.

## Proposed action

- **Rename the field to match what it carries** — `signal_qgate_count`, or explicitly
  `signal_qgate_pending_or_resolved_count`. This is the whole fix for the misread; the rest is defence
  in depth. Rename it at the gate, in the `lessons-capture` input table, and in the workflow body's
  runtime-inputs block together, so no surface keeps the old name.
- **Forward the derivation next to the verdict**: the per-phase `{phase, pending, counted, total}`
  breakdown and the resolution set actually summed. A count that carries its own breakdown is checkable
  by the body consuming it, and would have made this message unnecessary.
- **Narrow the must-not-recompute rule to its purpose.** It exists to avoid paying the query cost twice.
  It should not forbid a cheap reconciliation of a forwarded breakdown when the body is already reading
  those records for their content — which this body is instructed to do.
- Do **not** pursue the dispatch-ledger hypothesis. It is refuted: the value reproduces exactly from the
  Q-Gate store under the documented formula, and the matching `total_rows: 19` is coincidence.

## Evidence

- prompt body as dispatched — `signal_qgate_pending_count: 19`, `signal_automated_review_count: 1`,
  `signal_script_failure_clusters_count: 1`
- `phase-6-finalize/SKILL.md` item 4b.a Signal 1 — `signal_1_count = pending_subtotal + resolved_subtotal`
- `manage-findings qgate list --phase {…} --resolution pending` → `filtered_count: 0` on all five phases
- `manage-findings qgate list --phase {…} --resolution rejected` → 0, 1, 0, 0, 1 (sum 2)
- `manage-findings qgate list --phase {…}` (unfiltered) → `total_count` 1, 6, 0, 2, 12 (sum 21)
- 21 − 2 = 19, matching the forwarded value exactly
- aspect: logging_gap_analysis — `context_load_attribution: total_rows: 19` (coincidence, refuted above)
