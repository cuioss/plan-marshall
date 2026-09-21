# PLAN-CIS-036: D3's Split Says The Substrate Can Remove 7% — Measured On One Phase, And That Phase Is The Worst Case

epic: code-intelligence-substrate
workstream: WS-04

> Staged 2026-08-03 from the PLAN-CIS-030 landing (#1086). ⭐⭐ **This plan exists because the epic's
> own instrument produced a number that challenges the epic's value case.** Self-sufficient spec.

## Objective

`PLAN-CIS-030` shipped D3 — the separation of **index-answerable** exploration (which a code
substrate could plausibly remove) from **doc-residency** (which it cannot). On the one phase that
carried data:

| | bytes | share of exploration |
|---|---:|---:|
| `exploration_index_answerable_bytes` | 109,531 | **7.0%** |
| `exploration_doc_residency_bytes` | 975,401 | **62.5%** |
| `exploration_unattributed_bytes` | 476,922 | 30.5% |

⛔⛔ **If that generalises, this epic's flagship claim is wrong by roughly an order of magnitude.**
The roadmap premise was *"exploration is 76–85% of tool-result bytes"* read as *the substrate can
remove most of it*. This says the substrate's addressable share is **~7%**, while **62.5% is
documents a step must read to execute at all.**

**Get the split on the phases that decide the answer.**

## ⚠⚠ Why this is NOT yet a refutation — the reason is specific, not generic caution

**The one instrumented phase is `6-finalize`, which is precisely where doc-residency should be
HIGHEST.** Finalize is workflow-document-driven by construction: every step reads its own standard.
⇒ **This is plausibly the WORST CASE, not the typical case**, and the phases where a code substrate
would help most — `2-refine` (codebase orientation) and `5-execute` (implementation lookup) — are
**exactly the phases with no data**.

⛔ **So the honest state is: the epic's value case is neither confirmed nor refuted, and it is now
measurable.** Treating 7% as the answer would be as wrong as treating 76–85% as the answer was.

## Why only one phase has data (do not re-derive this)

`record-metrics` runs at `order: 998` — after the merge and after the cache sync — so only the
finalize bucket was written by the newly-landed code. Phases 1-init…5-execute carry **no
`cache_read_input_tokens` field at all** (absent, not zero). ⭐ **This is the non-self-exercisability
rule (lesson `2026-08-03-06-004`) landing on the instrument itself**, and it is expected, not a
defect. ⇒ **Any plan composed after #1086 emits all six phases; this plan needs those, not a re-run of
the old corpus.**

## ⭐⭐⭐ THE COMPOSITION CLAIM IS NOW FIRST-PARTY (folded 2026-08-03 from an operator-supplied `metrics.md`)

**Independently recomputed by this orchestrator from `plan-45-demo-client-doc-consolidation` — a plan
NEITHER epic ran** — using the billing formula `input + output + 1.25·cache_creation + 0.1·cache_read`
over all six phase blocks:

| component | this plan | `truthful-signals` n=47 (was second-hand) |
|---|---:|---:|
| `cache_read` | **73.15%** | 76.1% |
| `cache_creation` | 25.69% | 22.8% |
| `output` | **1.13%** | 1.1% |
| `input` | 0.03% | — |

⭐ **The recomputed billing total matched the file's published per-phase sum to ONE token**
(66,212,048 vs 66,212,049), which verifies the formula itself, not just the shares.

⇒ ⭐⭐ **"~99% of billing weight is context, not generation" is no longer a lead.** It is confirmed
first-party on an independent plan, and it is the one premise the whole token programme rests on.
**Stop labelling it second-hand.** ⚠ The per-phase *ranking* remains suspect for the three recorded
reasons — this corroborates the **composition** only, which is exactly the figure predicted to survive.

### ⛔ And the same file REFUTES the exploration-share claim at the low end

Measured per phase: **85.4% / 74.8% / 57.2% / 80.4% / 73.1%** (2-refine → 6-finalize).

⇒ The claim *"exploration is 76–85% of tool-result bytes in EVERY phase from 2-refine onward"* is
**false at 4-plan (57.2%)**. The range is wider than reported and 4-plan is the outlier.
⛔ **D1 must report the per-phase RANGE, never a single band** — and note this is a second instance of
a phase-specific figure being generalised to all phases, which is this plan's founding concern.

⚠ **One number to watch, not to rely on**: `6-finalize` is **49.7%** of billing weight here, against
the 49.4% `truthful-signals` retired as suspect. Two independent plans agreeing is interesting —
**but this plan's `5-execute` is re-entered too**, so the same distortion applies. **Do not read it as
rehabilitating the ranking.**

## Deliverables

1. **D1 — GATE: collect the split across all six phases, over plans composed AFTER `9b689d65b`
   (mutates nothing).** Report the per-phase index-answerable / doc-residency / unattributed split
   **with the population size**, and state how many plans contributed to each phase.
   ⛔ **Do not pool phases into one headline** — the whole point is that the phases differ.
2. **D2 — settle the 30.5% unattributed.** Nearly a third of exploration bytes fall in neither
   bucket, which is large enough to flip the conclusion by itself. ⛔ **Until it is classified, the
   7% is a LOWER bound on the addressable share and must be reported as such**, never as the figure.
3. **D3 — state the epic's value case against the measurement, in either direction.** If the
   addressable share is small on the phases that matter, **say so and re-scope the epic** — this is
   the plan that is permitted to conclude the substrate is worth less than assumed. ⭐ **A measurement
   programme that cannot return an unwelcome answer is not one.**
4. **D4 — every figure names its population and its phase.** Inherited from CIS-030 D4; restated
   because this plan's whole risk is a phase-specific figure read as a whole-corpus one.

Four deliverables (D1 a gate) — below the split guard.

## Claim Labels

- **OBSERVED (first-party, read from `2026-08-03-context-byte-attribution-instrumentation/work/metrics.toon`)**:
  the three byte figures and their exact sum to `exploration_result_bytes` (1,561,854).
  - verdict: unverifiable | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: The source record has ROTATED OUT of the corpus: .plan/local/archived-plans/2026-08-03-context-byte-attribution-instrumentation/ no longer exists at HEAD, and the earliest archived plan still carrying metrics.toon locally is 2026-08-08. The cited 1561854-byte three-bucket sum therefore cannot be re-checked against its own source. Not refuted - unreachable.
- **OBSERVED (first-party)**: the `cache_read` attribution reconciles to the phase total **exactly,
  delta 0** — but on `6-finalize` only; the other five phases carry no such field.
  - verdict: unverifiable | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: Same rotated-out source as claim 0: the 2026-08-03-context-byte-attribution-instrumentation record is gone from HEAD's local corpus, so neither the 6-finalize cache_read reconciliation nor the absent-field claim about the other five phases can be re-checked against it.
- **HYPOTHESIS**: that `6-finalize` is the doc-residency worst case. **Plausible and unverified** —
  D1 is what confirms or refutes it (verify-at-outline). ⛔ **Do not assume it while scoping D3.**
  - verdict: contradicted | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: no | evidence: REFUTED by independent recomputation at HEAD. Using the 2026-08-09 self-review-resweeps metrics.toon, doc-residency by phase is 2-refine 90.7 percent and 3-outline 73.0 percent, BOTH exceeding 6-finalize at 64.5 percent. Two phases are worse, so 6-finalize is NOT the worst case - which is the spec's own title premise. The measurement remains valid; the superlative does not, and the spec must be re-scoped before it is emittable.
- ⛔ **Verify-first**: `truthful-signals`' `PLAN-TRUTH-055` — re-entered phase rows are
  arithmetically impossible — **binds here**. A per-phase figure over a re-entered phase is suspect
  regardless of instrumentation. **Check `close_count` per contributing phase and exclude or label.**
  - verdict: unverifiable | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: PLAN-TRUTH-055 belongs to the truthful-signals epic and sits outside this pass's readable scope, so the binding claim could not be settled at its source. The mechanism it names IS directly observable in this corpus though: 5-execute carries close_count 2 in the 2026-08-09 metrics.toon, so a re-entered phase row is real here even though the governing rule was not read.

## Expected Surface

- **OBSERVED**: `work/metrics.toon` in plans archived after `9b689d65b` — the read-only corpus
- **HYPOTHESIS**: `audit-archived-plan-retrospectives`' `billing-composition` check (24th), the
  natural host for a corpus-wide split report (verify-at-outline)

## Dependencies and Sequencing

- ✅ **HARD GATE RELEASED 2026-08-09.** ~~needs plans composed after `9b689d65b`; at staging there
  is at most one~~. **The population is now n=5**: five archived plans carry `work/metrics.toon`
  (`2026-08-08-absent-names-two-states-with-opposite-remedies`,
  `2026-08-08-daemon-baseline-interpreter-is-unregistrable`,
  `2026-08-08-provider-logging-path-containment`,
  `2026-08-09-self-review-resweeps-full-surface-every-round`,
  `2026-08-09-two-producers-one-marker-field-two-encodings`), and **at least one carries all six
  phases**. ⚠ The 08-08 anchor's *"the instrumented population is STILL n<=1"* is **stale** — it
  was true of the two cloud-lane landings (#1100, #1107) and has been overtaken by five local
  landings. ⛔ **D1 must still derive the population itself and publish it** — this note releases
  the gate, it does not supply the count.
- ⛔ **Never pair** with CIS-035, CIS-011, CIS-031 or CIS-034 — one WS-04 serialization class.
- **Adjacent**: `PLAN-CIS-002`/`CIS-024` consume the answer; **neither should assume it.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-036-exploration-split-measured-on-one-phase-and-it-is-the-worst-case.md"
```

## ⛔⛔⛔ THE CENTRAL HYPOTHESIS IS HALF-CONFIRMED AND HALF-REFUTED — corrected 2026-08-09 from the PLAN-CIS-031 landing (#1126)

**The first six-phase instrumented record now exists, and it does NOT say what this spec
predicted.** Recomputed first-party by the orchestrator from
`.plan/local/archived-plans/2026-08-09-self-review-resweeps-full-surface-every-round/work/metrics.toon`
(**n=1 plan**, all six phases, `close_count: 1` on every row except `5-execute` = 2):

| phase | exploration % of tool-result bytes | index-answerable | doc-residency | unattributed |
|---|---:|---:|---:|---:|
| 2-refine | 80.5% | **3.3%** | **90.7%** | 6.0% |
| 3-outline | 78.4% | 16.8% | 73.0% | 10.2% |
| 4-plan | 80.2% | **0.0%** | 43.9% | 56.1% |
| 5-execute ⚠ | 82.2% | **33.6%** | 59.5% | 6.9% |
| 6-finalize | 74.2% | 13.8% | 64.5% | 21.6% |
| **whole plan** | ~77% | **15.9%** | **65.2%** | 18.9% |

**✅ CONFIRMED half**: `5-execute` is the best case for the substrate at **33.6%**, exactly as
this spec predicted the implementation-lookup phase would be.

⛔ **REFUTED half, and it is the load-bearing one**: this spec's § "Why this is NOT yet a
refutation" rests on *"`6-finalize` … is plausibly the WORST CASE"* and on
*"`2-refine` … where a substrate would help most"*. **`2-refine` is the WORST phase in the plan
— 3.3% index-answerable, 90.7% doc-residency — and `6-finalize` is not the worst case at all;
two phases are worse.** ⇒ ⛔ **Do NOT carry the worst-case framing into D1's scoping.** Refine is
a documentation-reading phase, not a codebase-orientation phase, and the spec assumed otherwise.

⭐ **The whole-plan addressable share is 15.9%** — 2.3× the 7.0% that alarmed the epic, still an
order of magnitude below the roadmap premise, **and dwarfed 4:1 by doc-residency.** D3's
obligation ("state the epic's value case against the measurement, in either direction") now has
its answer available and it is unwelcome. ⇒ **`PLAN-CIS-039` (WS-06) was staged to own the 65.2%
bucket** — D3 must reconcile with it rather than re-derive it.

### ⛔ D2's "30.5% unattributed" names ONE of TWO different populations

Unattributed **bytes** are 18.9% on this plan. Unattributed **`cache_read`** is **65.9%** across
all phases and **≥83% in every phase except `6-finalize`** (40.5%). **These are different
quantities with different denominators and D2 currently names only the first.**
⇒ ⛔ **`PLAN-CIS-042` D1 owns separating them, and this plan CONSUMES that separation.**
Until CIS-042 lands, **D2's scope is the byte half only — say so, do not silently widen it.**

### ⛔ Two schema obligations D1 inherits, both breaking

From `metrics-record-cannot-represent-re-entered-phase` (epic `truthful-signals`):

1. `partial` / `unrecorded_phases` are **RENAMED** to `any_phase_missing_end_time` /
   `phases_missing_end_time`, **with no dual-key shim**. Archived records still carry the old
   keys. ⇒ **D1 must implement the three-state read** (`current` / `old-schema` / `pre-#812`) and
   **report `old-schema` explicitly** — ⛔ *"defaulting an old-schema record is how a bare rename
   manufactures a clean verdict out of an absent key"*, which is this epic's own archetype.
2. The four per-dispatch context-load columns **no longer default to `0`** when their flag is
   omitted — an unmeasured column carries the literal `unmeasured`. ⇒ **three-way cell read**
   (measured / unmeasured / unrecognised). A measured `0` is still `0`.

⭐ **Also newly available and directly relevant to D1's `close_count` obligation**: `value_scope`
(`single_close` | `mixed_cumulative_and_last_close`) plus `cumulative_fields` /
`last_close_fields` are now written per phase row. **Use them rather than hand-deriving which
figures a re-entered row blends** — that is exactly the discriminator this spec's verify-first
clause asks for.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
See `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
