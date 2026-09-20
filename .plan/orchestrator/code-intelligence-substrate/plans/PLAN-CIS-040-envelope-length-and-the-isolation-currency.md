# PLAN-CIS-040: Cost Is Bytes × Turns, And Nothing Owns The Turn Factor

epic: code-intelligence-substrate
workstream: WS-06

> Staged 2026-08-09 from the PLAN-CIS-031 landing (#1126). Self-sufficient spec.

## Objective

A byte costs `1.25×` on entry (`cache_creation`) and `0.1×` on every subsequent turn
(`cache_read`). So the price of a byte is:

```text
cost(byte) = 1.25 + 0.1 × turns_remaining
```

Measured on #1126: **842,558,977 `cache_read` against 18,876,879 `cache_creation` — the
average byte is re-read 44.6 times**, so the average byte costs **~5.7×** and a byte entering
early in `5-execute`'s ~122-turn envelope costs **~13.4×**.

⇒ ⭐⭐ **`turns_resident` is a first-class cost factor, it varies by more than 3× across
envelopes, and no plan in a 30-row queue owns it.** Every lever the epic has staged targets
the byte count. This plan targets the other factor.

## The decomposition, per phase (OBSERVED, first-party)

`cache_read / tool_uses` is the average resident context per API call; the phase row already
carries the turn count. Their product **is** the read cost, so this is a decomposition rather
than a correlation — and both factors are separately attackable where the single number was not:

| phase | billing | share | resident ctx | turns | turns/envelope | `cache_creation` % of phase |
|---|---:|---:|---:|---:|---:|---:|
| 1-init | 1.01M | 0.9% | ~252K | 37 | inline | 6.4% |
| 2-refine | 3.06M | 2.8% | 237K | 94 | ~47 | 25.0% |
| 3-outline | 11.72M | 10.8% | 359K | 244 | ~61 | 23.8% |
| 4-plan | 11.20M | 10.3% | 273K | 140 | ~70 | **65.4%** |
| 5-execute ⚠ | 28.36M | 26.1% | **696K** | 365 | **~122** | 9.8% |
| 6-finalize | 53.50M | 49.2% | **721K** | 598 | ~37 | 18.4% |

⚠ `5-execute` is re-entered (`close_count: 2`) — `PLAN-TRUTH-055` binds, so its row is
**labelled, not quoted as a rate**. The turn factor's *existence* does not depend on it.

**The arithmetic that makes this a lever**: splitting one 122-turn envelope into four 30-turn
envelopes cuts the multiplier on every byte that does not need to survive the whole run from
**13.4× to 4.15×**. The cost of doing so is re-creating the skill stack three extra times —
**~12.5K tokens × 1.25 × 3 ≈ 47K**, against a `5-execute` phase costing 28.4M. ⇒ **The
isolation boundary is nearly free and is being under-used.**

## ⭐⭐ The second finding: § 6 defends the biggest bet in the wrong currency

`doc/concepts/token-management.adoc` § 6 calls per-dispatch isolation *"the biggest single
token-management lever"* and defends it with:

> *"a plan that would consume 30-50 K tokens … in a single-context shape consumes ~6 K
> orchestrator-side … each variant's larger context being independent — and never additive"*

Never additive **to the orchestrator**. Entirely additive **to the bill**. ⇒ **The document
argues in orchestrator-context-size while the epic has established that the cost driver is
billing weight, of which context is 99.08%.** That is doc-contract-divergence on the system's
single largest architectural bet.

⭐ **The bet is almost certainly still correct — but for a reason § 6 does not state.**
Isolation does not make a byte cheaper; it **bounds how many turns a byte is re-read for.**
That argument is stronger *and* quantifiable, and it is the one this plan's measurement
supports. ⛔ **Do not weaken the isolation claim — restate it in the currency that was measured.**

## ⛔ The `4-plan` inversion — a live anomaly this plan must not silently absorb

`4-plan` spends **65.4% of its billing weight on cache _creation_**, against 6–25% everywhere
else, at a read/creation ratio of **6.5** versus 36–180 elsewhere. Something in `4-plan`
repeatedly creates large prefixes that are read back only ~6 times. **The mechanism is
unknown.** ⛔ **Read the mechanism — do not infer it from the ratio** (lesson
`2026-08-03-19-001`: a timing or a ledger entry is a proxy and is silent about which mechanism
produced it). D3 owns it, and **a refutation is a valid outcome**.

## Deliverables

1. **D1 — GATE: publish the two factors, mutates nothing beyond the report.** Establish
   `resident_context` and `turns` per phase and per envelope across the post-`9b689d65b`
   archived plans (**n=5 at staging**), with the population per phase. ⛔ **Exclude or label
   every re-entered row** (`close_count > 1`) per `PLAN-TRUTH-055`; the new `value_scope` /
   `cumulative_fields` / `last_close_fields` discriminators from
   `metrics-record-cannot-represent-re-entered-phase` are the sanctioned way to do it.
   ⛔ **Report the per-phase RANGE, never a single band** — this plan's own founding concern.
2. **D2 — restate `token-management.adoc` § 6 in the measured currency.** Per-dispatch
   isolation bounds `turns_resident`; that is the claim the data supports. ⛔ **Keep the
   isolation recommendation intact** — this is a correction to the argument, not to the design.
   ⚠ Also check § 6's *"~6 K orchestrator-side"* and *"10-15 K tokens of skill bodies"* figures
   against D1 and either re-derive or delete them; a restated figure about a moving system is
   the archetype `PLAN-CIS-031` spent 1.5M tokens learning to delete rather than correct.
3. **D3 — settle the `4-plan` creation inversion.** Read the mechanism. Either name it and
   state whether it is addressable, or record it as refuted. ⛔ **Do not ship a remedy for a
   mechanism that was inferred rather than read.**
4. **D4 — one envelope-length lever, chosen by D1.** Land the single highest-`bytes × turns`
   envelope split D1 identifies. ⛔ **The split must preserve what is examined** — the same
   work in shorter-lived contexts, never less work. ⚠ **A dispatch boundary is not free of
   *quality* cost even when it is nearly free of *token* cost**: a leaf cannot see the previous
   leaf's reasoning. **State what each split envelope loses, and do not split across a boundary
   where continuity is load-bearing.**

Four deliverables, D1 a gate — below the split guard.

## Claim Labels

- **OBSERVED (first-party, recomputed from #1126's `work/metrics.toon` by the orchestrator)**:
  every figure in both tables; the billing recompute **108,860,688** against the file's own
  published sum **108,860,690** (two-token delta, rounding) — which verifies the formula, not
  only the shares.
- **OBSERVED (first-party, `execution-context.md`)**: the dispatch token order is variant system
  prompt → **volatile prompt body** (`plan_id`, `WORKTREE`, `name`, task-specific inputs) →
  Step 2 persona load → Step 3 `skills[]` → Step 4 workflow `Read`. The largest stable payload
  sits **behind** the volatile fields, so cross-dispatch prefix sharing is impossible past the
  system prompt.
- ⛔ **REJECTED, MEASURED — do not stage a plan for it.** The above is a real structural defect
  and is **worth ~0.39% of the bill**: ~27 dispatches × ~12.5K skill stack ≈ 337K creation ≈
  421K billing-weighted against 108.9M. In `6-finalize`, creation runs ~493K **per dispatch**,
  of which the skill stack is 2.5% — **97.5% of creation is in-conversation growth, not prefix
  re-creation.** Recorded so the lever is not re-proposed. → `epic.md` § Open Decisions.
- **HYPOTHESIS**: that shortening an envelope reduces total cost rather than relocating it.
  ⚠ **The failure mode is real**: if a split envelope must re-read the same context to do its
  half of the work, the split converts cheap `cache_read` into expensive `cache_creation` and
  **costs more**. **D1 must identify a split where the second half genuinely does not need the
  first half's residency** — that, not the arithmetic, is D4's real gate.
- **HYPOTHESIS**: that `4-plan`'s inversion has a single nameable mechanism. Unverified. D3.

## Expected Surface

- **OBSERVED**: `work/metrics.toon` in plans archived after `9b689d65b` — read-only (D1)
- **OBSERVED**: `doc/concepts/token-management.adoc` § 6 (and § 4's figures) — D2
- **HYPOTHESIS**: the phase whose envelope D1 selects — `phase-5-execute`'s task loop and its
  bin-packer, or a `phase-6-finalize` step chain (verify-at-outline). ⚠ **The per-envelope
  packing budget is already operator-tunable** (`doc/user/configuration.adoc#per-envelope-packing-budget`)
  — **check whether D4 is a config default rather than a code change** before scoping either.
- **HYPOTHESIS**: `manage-metrics` emission of the two factors — ⛔ **only if `PLAN-CIS-042`
  has not already landed them.** Coordinate; do not add a second writer.

## Dependencies and Sequencing

- ⛔ **`PLAN-CIS-042` (WS-04) should land first.** It owns the `resident_context` / `turns`
  emission and the two `unattributed` populations; D1 reads both. If CIS-042 has not landed,
  D1 derives them read-only and **must not add a writer**.
- ✅ **MAY pair with `PLAN-CIS-039`** (same workstream, disjoint surfaces) — ⚠ both touch the
  `execution-context` agent body; re-verify the file set at emit.
- ⛔ **Never pair with any WS-04 plan.**
- **Adjacent to `PLAN-CIS-035`**: that plan targets the cost of dispatches that produced
  nothing; this targets the cost of dispatches that ran too long. Different mechanisms, neither
  subsumes the other. ⛔ **CIS-035's own premise is under correction — see its spec.**

## Anti-goals

- ⛔ **Do not reduce what is examined.** A shorter envelope must do the same work.
- ⛔ **Do not weaken per-dispatch isolation.** D2 corrects the argument, never the design.
- ⛔ **Do not stage the cache-prefix reordering.** Measured at 0.39%; recorded as rejected.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-040-envelope-length-and-the-isolation-currency.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
See `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
