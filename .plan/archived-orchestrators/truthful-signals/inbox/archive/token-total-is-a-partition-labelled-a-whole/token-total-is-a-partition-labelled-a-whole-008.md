envelope_version=1
sender_type=plan
sender_id=token-total-is-a-partition-labelled-a-whole
epic=truthful-signals
kind=candidate-lesson
created=2026-08-03T12:53:52Z

component=plan-marshall:phase-6-finalize
category=bug
bundle=plan-marshall

# The retrospective reads the measurements three steps before they are finalized — so a plan about measurement truth audited itself against a stale, un-enriched store

## What was observed

`phase_6.steps` for this plan ordered the finalize steps as:

| # | step |
|---|------|
| 16 | `branch-cleanup` |
| 17 | `plan-marshall:plan-retrospective` |
| 20 | `record-metrics` |

`record-metrics` is the step that closes the final phase boundary and runs `manage-metrics enrich`. It runs **three positions after** the retrospective that consumes its output. The consequences are all observable in this plan's own artifacts:

1. **`metrics.md` was stale by ~3 hours at read time.** It carries `Generated: 2026-08-03 09:22:33 UTC`; the finalize ran until 12:39. It rendered `Closes: 2` for `5-execute` while `work/metrics.toon` records `close_count: 3`.
2. **`6-finalize` is understated by ~1.03M tokens.** `metrics.toon` records `dispatch_boundary_rows_recorded: 8` and `dispatch_boundary_total: 1345299`; the on-disk `metrics-dispatch-boundaries-6-finalize.toon` carries **13 rows summing 2,372,638**.
3. **Every `enrich`-produced field is absent from every phase row.** No `subagent_samples`, no `input_tokens`/`output_tokens`/`cache_read_input_tokens`/`cache_creation_input_tokens`, no `billing_weighted_total`.

Item 3 is the one that matters, because two of this plan's own deliverables consume exactly those fields:

- **D4** (declare partiality) compares `rows_recorded` against `subagent_samples`. With `subagent_samples` absent, the comparison never runs and every phase renders `coverage undecidable — the phase carries no subagent_samples to compare against`.
- **D5** (surface `billing_weighted_total` as a first-class cost figure) renders a `Billing (cost)` column that is `-` for all six phases.

Both deliverables shipped, passed verification, and are **operationally inert in their own plan's output**. The plan was raised because the operator asked *"why did this cost so much?"* and the report answered only the work question. After the fix, the report has a cost column — and it is empty.

## Why the verification did not catch it

Deliverable 7's criterion was *"the Billing column is present and never folded into the Tokens Total."* Both halves are satisfied by an **empty** column. The criterion tested the column's existence and its non-contamination of the Total; nothing tested that it carried a number. A presence assertion over a structurally-absent value passes for the same reason a vacuous guard passes.

## The generalisable rule

**A step that consumes a measurement must run after the step that finalizes it — and when it cannot, its report must say which figures are provisional.**

Two checks worth making standing practice:

1. **Order the consumer after the producer, or declare the read stale.** `plan-retrospective` should either move after `record-metrics`, or `manage-metrics generate` should stamp the report with its store's `updated` timestamp so a consumer can detect that it is reading a snapshot older than the store. The staleness here was recoverable only by hand-comparing an embedded `Generated:` line against `metrics.toon`'s `updated:` key.
2. **A deliverable whose output is a field must be verified against a populated field.** "Column present" and "column correct" are different assertions; when the producing pipeline did not run in the verifying window, only the first is testable, and passing it proves nothing about the second. Prefer a fixture that forces the producer to have run.

## Impact

Structural and every-plan, not specific to this one: the ordering is in the composed manifest, so **every** plan's retrospective reads a pre-`record-metrics`, pre-`enrich` store. Every budget verdict this project's retrospective has issued — including the three `[BUDGET]` warnings this very retrospective emitted — is computed against a floor, not a total.

That is the same defect class the plan was raised to fix, relocated from the renderer to the step order: the retrospective's `totals.tokens` is a partition, and nothing in the report says so.
