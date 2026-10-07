# PLAN-CIS-042: Two-Thirds Of The Attributed Quantity Is Unattributed, And The Cost Has No Decomposition

epic: code-intelligence-substrate
workstream: WS-04

> Staged 2026-08-09 from the PLAN-CIS-031 landing (#1126) — the epic's first six-phase
> instrumented record. Self-sufficient spec.

## Objective

`PLAN-CIS-030` D2's reconciliation identity is real and was re-verified here on `6-finalize`:
`136,811,943 + 7,731,849 + 66,732,634 + 45,218,522 + 0 + 174,503,179 = 430,998,127` =
`cache_read_input_tokens`, **delta zero**. It holds because `cache_read_unattributed` is a
catch-all, and that is where the quantity lands:

| phase | `cache_read_unattributed` share |
|---|---:|
| 2-refine | 83.3% |
| 3-outline | 91.6% |
| 4-plan | 90.7% |
| 5-execute ⚠ | **97.4%** |
| 6-finalize | 40.5% |
| **all phases** | **65.9%** |

⛔⛔ **The instrument attributes usefully in exactly one phase — the phase it was built and
tested against.** Outside `6-finalize` it is ≥83% unattributed. That is this epic's own
signature archetype (*verified on one phase, generalised to six*) landing on the instrument
for the **second** time; the first was reading an absent field as zero inside the verification
of the plan that shipped it.

⭐ **And there are TWO different `unattributed` numbers that are not the same number.**
Unattributed *bytes* are **18.9%**; unattributed *`cache_read`* is **65.9%**.
`PLAN-CIS-036` D2 says *"settle the 30.5% unattributed"* and names only one of them.

## The second half: the cost has an actionable decomposition nobody emits

`cache_read / tool_uses` is the average **resident context** per API call; the phase row already
carries the **turn** count; their product is the read cost. Both factors are derivable today and
neither is published, so every consumer sees one opaque number instead of the two levers inside it.

| phase | billing share | resident ctx | turns | `cache_creation` % of phase |
|---|---:|---:|---:|---:|
| 1-init | 0.9% | ~252K | 37 | 6.4% |
| 2-refine | 2.8% | 237K | 94 | 25.0% |
| 3-outline | 10.8% | 359K | 244 | 23.8% |
| 4-plan | 10.3% | 273K | 140 | **65.4%** |
| 5-execute ⚠ | 26.1% | **696K** | 365 | 9.8% |
| 6-finalize | 49.2% | **721K** | 598 | 18.4% |

## Deliverables

1. **D1 — GATE: name and separate the two unattributed populations.** Report unattributed
   *bytes* and unattributed *`cache_read`* as distinct, separately-named quantities with their
   own denominators, everywhere either is emitted or rendered. ⛔ **Until this lands, no
   consumer may quote "the unattributed share" without saying which one** — and
   `PLAN-CIS-036` D2 must be read as covering the byte half only.
2. **D2 — attribute `cache_read` outside `6-finalize`, or state why it cannot be.** Establish
   the mechanism behind the ≥83% unattributed share in the other five phases. ⛔ **Read the
   mechanism — do not infer it** (lesson `2026-08-03-19-001`). ⭐ **"It cannot be attributed
   there, and here is why" is a valid and valuable outcome** — what is not valid is an identity
   that reconciles into a catch-all while reading as attribution.
3. **D3 — emit `resident_context_tokens` and `turns` per phase, and settle the `4-plan`
   inversion.** Publish both factors rather than leaving them derivable-in-principle.
   ⚠ `4-plan` spends **65.4%** of its billing weight on cache *creation* against 6–25%
   elsewhere, at a read/creation ratio of 6.5 versus 36–180 — **mechanism unknown, and this
   deliverable is where it gets read.** ⛔ Coordinate with `PLAN-CIS-040` D3, which carries the
   same anomaly from the consuming side: **one writer, and it is here.**
4. **D4 — every figure names its population, its phase, and its sampling point.** Inherited from
   CIS-030 D4 and CIS-036 D4; restated because this plan's whole subject is a quantity whose
   denominator was never named. ⛔ **Adopt the vocabulary already shipped by
   `metrics-record-cannot-represent-re-entered-phase`** — `value_scope`,
   `cumulative_fields` / `last_close_fields`, `{denominator}_sampling_point` — rather than
   introducing a parallel one. ⚠ That plan also **renamed** `partial` / `unrecorded_phases` to
   `any_phase_missing_end_time` / `phases_missing_end_time` **with no dual-key shim**, so any
   read of an archived record must implement the three-state read (`current` / `old-schema` /
   `pre-#812`) and report `old-schema` explicitly.

Four deliverables, D1 a gate — below the split guard.

## Claim Labels

- **OBSERVED (first-party, recomputed by the orchestrator from
  `.plan/local/archived-plans/2026-08-09-self-review-resweeps-full-surface-every-round/work/metrics.toon`)**:
  every figure in both tables; the `6-finalize` reconciliation sum; the billing recompute
  108,860,688 against the file's published 108,860,690.
- **OBSERVED**: the composition — `cache_read` 77.40% / `cache_creation` 21.68% / `output`
  0.92% / `input` 0.006%, i.e. context is **99.08%** of billing weight. Third independent
  first-party confirmation. ⚠ Composition only; the per-phase **ranking** stays retired.
- ⚠ **`5-execute` is re-entered on this plan** (`close_count: 2`), so its row is subject to
  `PLAN-TRUTH-055` and is **labelled, never quoted as a rate**. It is also the phase with the
  most extreme unattributed share, so **D2 must not rest its mechanism on that row alone.**
- **HYPOTHESIS**: that the ≥83% unattributed share generalises beyond **n=1 plan**. D2 must
  establish it across the post-`9b689d65b` population (**n=5 at staging**) before scoping a fix.
- **HYPOTHESIS**: that `4-plan`'s creation inversion has a single nameable mechanism. Unverified.

## Expected Surface

- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/manage-metrics/` — the emission and the
  `standards/data-format.md` contract
- **OBSERVED**: `work/metrics.toon` in plans archived after `9b689d65b` — read-only corpus
- **HYPOTHESIS**: `plan-retrospective` render path — **only where a figure is rendered without
  being persisted.** ⛔ `PLAN-CIS-020` owns the render path and `PLAN-CIS-022` owns the
  ledger-disagreement half — **coordinate, do not overlap.**
- **HYPOTHESIS**: `audit-archived-plan-retrospectives`' `billing-composition` check
  (verify-at-outline)

## Dependencies and Sequencing

- ⛔ **WS-04 serialization class — never pair with** CIS-010, CIS-011, CIS-012, CIS-013,
  CIS-019, CIS-020, CIS-022, CIS-034, CIS-035, CIS-036, CIS-037, CIS-038.
- ⭐ **Should land BEFORE `PLAN-CIS-039` and `PLAN-CIS-040`** (WS-06) wherever a figure is
  load-bearing — both read these fields to size themselves. Neither is hard-blocked: each can
  derive read-only, and **must not add a second writer** if this has not landed.
- **Adjacent to `PLAN-CIS-036`**: that plan consumes the byte split, this one separates the two
  populations it is stated in. ⛔ **CIS-036's D2 covers the byte half only** — do not read it as
  covering `cache_read`.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-042-attribution-populations-and-the-cost-decomposition.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
See `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
