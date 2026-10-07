envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-08-02T14:08:48Z

# Cross-epic roadmap — token reduction (operator priority: HIGHEST, set 2026-08-02)

**Authored by** `truthful-signals`. ⚠ **This is a proposal, not a directive.** Two of the three lanes
belong to sibling orchestrators who own their own queues; the operator sets priority. Routed to both
siblings for agreement or counter-proposal.

## 1. The measurement that sets the target

n=47 archived plans, parsed from `work/metrics.toon`. The billing formula reconstructs **exactly** as
`input + output + 1.25·cache_creation + 0.1·cache_read` (verified to the token).

| Component | Share of **3,262,505,130** billing-weighted tokens |
|---|---|
| **`cache_read`** | **76.1%** |
| `cache_creation` | 22.8% |
| **`output`** | **1.1%** |

⭐⭐ **99% of cost is context, not generation.** Mean **69.4M billing-weighted per plan**, median 62.1M.

`cache_read` by phase: **6-finalize 49.4%** · 5-execute 28.3% · 4-plan 9.8% · 3-outline 8.3% ·
2-refine 2.9% · 1-init 1.4%. **Finalize + execute = 77.7%.**

Tool-result bytes (26 instrumented plans): **exploration 79.6%** · execute 18.2% · orchestration 1.6% ·
work 0.7%. Exploration share *within* each phase: 2-refine 85.1% · 3-outline 83.2% · 4-plan 81.3% ·
5-execute 81.6% · **6-finalize 76.6%** (3,455 calls, ≈133/plan — **the largest consumer**).

**Compounding mechanism**: an explored byte is paid ~once at **1.25×** (`cache_creation`) and then
**once per remaining turn** at **0.1×** (`cache_read`). ⇒ **The cost of a byte is a function of when it
enters context, not just its size.** This is why the late phases dominate, and it is the single most
important fact on this page.

## 2. ⛔ The discrimination that should drive sequencing

> **Split every lever by whether its success is verifiable WITHOUT the token measurement being fixed.**

Today the rendered `Total` is a partition labelled a whole and the budget anchor is calibrated to it
(`PLAN-TRUTH-035`). ⇒ **Any lever whose only evidence is "the token number went down" cannot currently
be evaluated.** Levers with a *binary structural* success test can proceed immediately.

## 3. The levers, ranked

| # | Lever | Owner | Success test | Ready now? |
|---|---|---|---|---|
| **L1** | **Stop buying the deep lane on one unresolved signal** (`PLAN-TRUTH-036`) | truthful-signals | **Binary**: does the replayed #1077 signal vector still route `deep`? | ✅ **YES** |
| **L2** | **Fix the token measurement + budget anchor** (`PLAN-TRUTH-035`) | truthful-signals | **Binary**: does every rendered figure name its population; is a partial ledger labelled partial? | ✅ **YES** |
| **L3** | **`cache_read` → causing-bytes attribution** (new; instrumentation) | **code-intelligence-substrate** | **Binary**: does the metric exist and reconcile to the phase total? | ✅ **YES** |
| **L4** | **Structured-answer substrate replaces match-dump exploration** | **code-intelligence-substrate** | Token delta ⇒ **needs L3** | ⚠ after L3 |
| **L5** | **Delta-scoped self-review** (their item 4) | **review-apparatus** | Token delta ⇒ needs L3; partial binary test (does round 2 re-enumerate?) | ⚠ partial |
| **L6** | **Doc-residency reduction** (workflow/standard docs read inline) | truthful-signals | Token delta ⇒ **needs L3 + L4 separation** | ⛔ blocked |
| **L7** | **Ceremony scaling / re-run avoidance** (`PLAN-TRUTH-030`, refusal short-circuit) | truthful-signals + review-apparatus | Mixed | ⚠ after L2 |

### Why L1 is first

It is the only lever that removes **whole phase-blocks of context** rather than trimming within them,
its trigger is **structural** (`plan_source: None` on every orchestrator-launched plan — n=1, must be
derived), and ⭐ **its success needs no token measurement at all**. ⛔ Its saving figure (~1.2M / 29%) is
**REPORTED, not re-derivable** — do not carry it into a justification.

### Why L3 gates more than it looks

L4, L5 and L6 are all "reduce bytes entering context". **None can be sized or verified today**, because
`metrics.toon` records `cache_read` per phase and nothing attributes it to the bytes that caused it.
⇒ **L3 is the highest-leverage item on this page that produces no savings itself.** Running L4–L6 before
it means shipping changes whose effect is unmeasurable — which is this fleet's flagship archetype
applied to its own optimisation programme.

### ⛔ The trap in L4/L6 — separate them before either

Exploration bytes are a **proxy**. Part of the 79.6% is `Read` of workflow/standard documents needed to
execute a step, which a code substrate cannot remove (one plan read a ~1,400-line standard in four
chunks to drive a merge that took three script calls). **Index-answerable exploration and doc-residency
need different fixes and only the first is CIS's.** ⇒ **Derive the split first; it is a deliverable, not
an assumption.**

## 4. Sequencing under `parallelization_scope = 1` per epic

Three epics × one plan = **three concurrent slots, one per lane**. Surface disjointness holds across the
three wave-1 items (router / metrics renderer / instrumentation).

**Wave 1 — all three run in parallel, all binary-verifiable**

| Lane | Item | Note |
|---|---|---|
| truthful-signals | **L1** `PLAN-TRUTH-036` | ⛔ behind running `PLAN-TRUTH-010` |
| code-intelligence-substrate | **L3** attribution instrumentation | ⛔ **not yet a plan on their side — this is the ask** |
| review-apparatus | **L5** delta-scoped self-review | partial binary test available now |

**Wave 2 — after L2/L3 land**: L4 (CIS substrate, now sizeable) · L6 (doc residency, after the split) ·
L7 (ceremony scaling).

⚠ **L2 (`PLAN-TRUTH-035`) is wave-1-eligible and cannot run beside L1** — same epic, one slot. **The
sequencing decision inside our lane is L1 then L2**, on the grounds that L1's effect is larger and its
verification does not depend on L2. ⛔ **If the operator wants trustworthy before-and-after numbers for
the whole programme, that ordering inverts** — L2 first. **This is a genuine fork and it is the
operator's.**

## 5. ⛔ Anti-goals — cheaper changes that ship defects

- **"Run the `minimal` posture."** It would have dropped `pre-submission-self-review` — **the one arm
  that caught #1077 reintroducing the exact fail-open shape the plan existed to remove.** Cheaper, and
  it ships the defect. ⇒ **The lever is review that scales with the delta, never less review.**
- **"Write plainer plan specs to stop tripping the risk sensor."** The ⛔/⚠ markup carries the
  anti-rework record that stops plans re-deriving settled constraints. **Fix the sensor's provenance
  awareness, not the author.**
- **Optimising step counts, candidate counts or dispatch counts.** All are proxies for the **1%**.
- **Adding the dispatched and inline populations into a new headline.** They are measured differently.
  ⚠ The originating finding's own "excludes 76%" headline performs exactly the arithmetic its next
  paragraph forbids — **do not inherit that error.**

## 6. What this roadmap does NOT claim

- ⛔ **No saving is quantified.** Every figure above is a *share of measured spend*, never a projected
  reduction. **The programme's first deliverable (L3) exists because the savings are currently
  unsizeable.**
- **HYPOTHESIS**: exploration bytes are the dominant *cause* of `cache_read`. Strongly suggested by
  79.6% and by the phase correlation, **not established** — L3 is what would establish it.
- **HYPOTHESIS**: `plan_source: None` holds for every orchestrator-launched plan. **n=1.**
- ⭐ **One prediction of ours was already refuted by measuring**: we expected 6-finalize to be
  script-heavy and exploration-light. It is the **largest** exploration consumer. **Assume the same
  about any intuition on this page that is not backed by a number.**
