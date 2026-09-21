envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=finding
created=2026-08-01T21:28:26Z

## Hand-off to `PLAN-TRUTH-010`: the false-fresh hole is NOT closed, and is now WORSE-ATTRIBUTED

**Type**: serialization-pair hand-off between two staged specs of this epic.
**Owner**: `PLAN-TRUTH-010` (owns the false-fresh hole).
**Emitter**: `PLAN-TRUTH-026` / `mandatory-plan-id-build-results-ledger`, PR #1075.

### The hole, restated

`PLAN-TRUTH-010` owns the defect where a **zero-exit `discover` / `run-config-key` call
stamps a `kind=build` success row** into the change ledger. The call did no build; its exit
code is zero because the lookup succeeded; the ledger records a successful build.

### What this plan changed, and why it makes the hole worse

`PLAN-TRUTH-026` did **not** close this hole — it was outside every deliverable's scope and
was deliberately left alone. But D3/D4 changed the *attribution* of the bogus row:

| | before `PLAN-TRUTH-026` | after `PLAN-TRUTH-026` |
|---|---|---|
| bogus `kind=build` row's `plan_id` | `null` | a **real plan id** |
| how the row reads | an orphan row of unclear provenance | **that plan's successful build** |

Before, a `null` plan_id was itself a weak tell that the row was not a genuine build.
After, the row is fully-formed and indistinguishable from a real successful build for the
named plan. The plan-id mandate improved every *genuine* row and simultaneously removed the
only accidental discriminator the *bogus* row had.

### Why this is a serialization constraint, not just a note

This is the reason the two specs are a pair and must be ordered deliberately:

- `PLAN-TRUTH-026` landing first is what creates the worse-attributed state, so the window
  between this landing and `PLAN-TRUTH-010` is a window in which the ledger contains
  confidently-attributed false build rows.
- Any detector `PLAN-TRUTH-010` builds must therefore be **population-derived over the
  post-#1075 ledger**, not over the pre-#1075 shape. A detector keyed on
  `plan_id IS NULL` — the obvious pre-#1075 heuristic — is now **vacuous**: it will match
  nothing and report clean.
- Ledger rows written between the two landings need a **backfill or re-classification
  pass**, because they cannot be distinguished after the fact by attribution alone.

### Recommended orchestrator action

- Raise `PLAN-TRUTH-010`'s queue priority relative to its pre-#1075 position — the cost of
  the hole went up when #1075 landed.
- Carry the `plan_id IS NULL` vacuous-detector warning into `PLAN-TRUTH-010`'s spec so the
  plan does not re-derive it, and so it does not ship a detector that was correct against
  the old population.
- Scope a ledger backfill/audit for the intervening window into `PLAN-TRUTH-010` rather
  than leaving it as follow-on residue.
