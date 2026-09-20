# Landing — PLAN-CIS-009

**PR** #1100 · merge commit `7a818deed` · corroborated as an ancestor of `origin/main`.
Ledger stamp followed as #1101 (`f6ec03442`) — see "Contract gap" below.

**Executed in the standalone cloud lane**, not the plan-marshall lifecycle — the first plan to run
that way. Cloud plan and run report were removed from `doc/plans/` at ingest; this record and the
orchestrator spec are the durable account.

## Outcome per deliverable

| D | Outcome |
|---|---|
| D1 — correct the enum in `manage-metrics/SKILL.md` | **No-op, premise refuted.** All three doc sites already list 11 values and the rejection sentence is already accurate — closed by #1083, guarded by `test_every_documented_termination_cause_site_matches_the_enum`. |
| D2 — correct the consumer | **Done.** `plan-retrospective/references/logging-gap-analysis.md` `DISPATCH_TERMINATION_CAUSE` brought to the full 11-value set. |
| D3 — pin it structurally | **Done, wider than specified.** Guards derive both sides and now cover the consumer *and* `data-format.md`, not only `SKILL.md`. Negative controls execute the guard itself, so the pins are non-vacuous. |
| D4 — sweep for siblings | **Done (recorded, not fixed).** Population published exactly. |

## The claim labels earned their keep

The plan's `HYPOTHESIS` — "the parser has 11 values and the SKILL documents exactly the first 6" —
was **half-confirmed and half-refuted**: 11 confirmed, "documents 6" refuted. Because the claim was
labelled and carried a named confirm/refute artifact, the run re-derived before acting and did **not**
rewrite a correct file to match a stale premise. D1 became a recorded no-op instead of damage.

⭐ The same premise sat in `PLAN-TRUTH-012` labelled **`OBSERVED`**, where nothing forced a re-check.
**A claim copied into a second plan does not inherit the first plan's verification**, and the
inherited `OBSERVED` is the more dangerous half. TRUTH-012 is now annotated and blocked from emission
until re-scoped.

## Deliverable-4 census — exact, reproducible

`148` argparse `choices=` call sites across `380` scanned files, `0` parse errors: `96` inline
literal, `52` name references (of which **50 are module-level named constants** — the drift-prone
shape — across ≥25 distinct constant expressions), `0` other. Derived by an AST walk, so comments,
docstrings and string literals never count; the script is reproduced in the run report and was
carried into this epic's records. An earlier approximate "~140" was **superseded** — a tilde cannot
support a completeness claim.

## Findings routed out

- **Two live sibling drifts, same defect class**, both missing `arch-constraint`:
  `manage-findings/SKILL.md` 12 documented vs `FINDING_TYPES` 14, and `manage-lessons/SKILL.md`
  3 vs `LESSON_CATEGORIES` 4. Spot-verified by the run, **not** by this orchestrator — leads to
  confirm at the named symbols. **Routed to `truthful-signals` PLAN-TRUTH-012**, which owns the
  class-retirement half. Recorded as a routing recommendation; **no fold performed**.
- **Systemic gap**: 50 named-constant `choices=` references have full-set prose mirrors with no
  doc-parsing guard. Retiring the whole class is an epic-level decision, not this plan's.
- **Plugin cache unsynced**: the run edited `marketplace/bundles/**` and a cloud session cannot
  write `~/.claude/`. A local `/sync-plugin-cache` is owed by whoever next works on a developer
  machine.

## Contract gap observed at landing

**The bridge's "stamp the row after the merge read-back" step is unperformable on the plan's own
branch** — the branch is merged and deleted by the time the read-back confirms, so the stamp needed a
second PR (#1101). Either the stamp moves to the orchestrator at ingest, or the bridge acknowledges a
follow-up PR. This is a defect in the rule as written, found by running it.
