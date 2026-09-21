# PLAN-CIS-014: The Dominant Script Cost Is Structurally Invisible — 59.5% Of Wall-Clock Below Every Threshold

epic: code-intelligence-substrate
workstream: WS-04

> Staged from the full-corpus audit (2026-07-26), lesson `2026-07-26-22-003`. **This is a cost
> finding AND an archetype instance**: the largest single cost in the script layer is invisible to
> every detector we have, because each individual call is far below the slow-call ceiling. The
> measurement machinery reports "no slow calls" truthfully while missing 59.5 % of the time spent.

## Objective

Two hot paths — `platform_runtime session` (**77,337 calls / 3 h 39 m**) and
`claude_pretooluse_hook` (**32,413 calls**) — together consume **59.5 % of all recorded script
wall-clock**. At **~0.17 s per call** neither ever trips the **30 s** slow-call ceiling, and neither
is visible in any per-plan view because the cost is spread across every plan. Make aggregate cost
visible, then reduce the largest lever.

## ⚠ Mechanism — audit-reported, NOT yet orchestrator-verified

The figures come from the audit's corpus-wide script-execution roll-up
(`.plan/local/audit-reports/20260726T202149Z.toon`). **D1 must re-derive them from the log corpus
before any optimisation is scoped** — the whole point of this plan is that unverified aggregate
numbers are what hid the cost in the first place.

- CLAIMED — `platform_runtime session`: 77,337 calls, 3 h 39 m cumulative.
- CLAIMED — `claude_pretooluse_hook`: 32,413 calls.
- CLAIMED — together **59.5 %** of all recorded script wall-clock; per-call ≈ **0.17 s**.
- OBSERVED (structural, first-party reasoning) — **the detector cannot see this by construction.**
  A per-call ceiling answers "is any single call pathological?" It is structurally incapable of
  answering "what dominates total time?" A cost that is 0.5 % of the ceiling and repeated 77,337
  times is *invisible by design*, not by oversight. **This is the same shape as PLAN-73's gate
  (comparison anchored to the wrong reference) and PLAN-CIS-016's detectors: the instrument is honest and
  the question is unanswerable with it.**
- OBSERVED — `session` is the terminal-title / session-binding seam this epic has already touched
  three times (PLAN-46 #994, PLAN-42 #988, and the orchestrator's own per-verb repaint). Its
  call volume is a direct consequence of repainting on every hook fire.

## Deliverables

### D1 — GATE: verify the numbers, then decide what to measure vs what to reduce (mutates nothing)

Re-derive the call counts, cumulative durations and share-of-total from the script-execution log
corpus **first-party** — do not scope from the audit's summary. Then settle two separable questions:
(a) **observability** — what aggregate view must exist so this class is visible next time (a
cost-by-script roll-up beside the slow-call ceiling); and (b) **reduction** — which of the two hot
paths is actually reducible, and by what mechanism (caching, debouncing, short-circuiting a no-op
repaint, or firing on fewer events). **Do not assume both are reducible**; a hook that must run on
every tool use may be irreducible in count and only reducible in per-call cost.

### D2 — aggregate cost is reportable

Add the roll-up D1 specifies: cumulative wall-clock and call count per script, ranked by share of
total, so a dominant-but-fast script is visible. The existing per-call slow-call ceiling stays —
this is an addition, not a replacement, and D1 must state how the two are read together.

### D3 — reduce the largest verified lever

Implement the D1-chosen reduction for whichever path D1 finds reducible. **Hard invariant: no
behavioural regression in the terminal-title / session-binding contract** — PLAN-46 (#994) fixed
title delivery onto the primary hook channel and PLAN-42 (#988) shipped the wait-mechanism stamp;
neither may regress. If the only available reduction risks either contract, D1 should prefer
observability (D2) alone and record why.

### D4 — tests

(a) The aggregate roll-up ranks a many-fast-calls script above a few-slow-calls script — the
assertion that fails against today's reporting. (b) The D3 reduction preserves the title/session
contract (assert delivery, not just absence of error). (c) A regression pin on the reduced path's
call count or per-call cost, whichever D1 made the target.

## Expected Surface

- HYPOTHESIS: `platform-runtime` `session` implementation and its hook-invocation site — the exact
  files depend on D1's reduction choice (verify-at-outline)
- HYPOTHESIS: the `claude_pretooluse_hook` registration/implementation (verify-at-outline)
- HYPOTHESIS: the script-execution logging / roll-up surface that would host D2 — likely
  `manage-logging` or the audit's reporting layer; D1 decides which owns it (verify-at-outline)
- OBSERVED: lesson `.plan/local/lessons-learned/2026-07-26-22-003.md`, retired at finalize
- OBSERVED: `.plan/local/audit-reports/20260726T202149Z.toon` — the source figures

⚠ **Surface is HYPOTHESIS-heavy by design** — D1's verification determines it. That makes this plan a
poor candidate for a light-lane route; see the note below.

**Disjointness:** depends on D1's outcome. **Presumed to touch `platform-runtime` and the hook layer**
— disjoint from PLAN-57 (`manage-status`), PLAN-75 (`manage-execution-manifest`), PLAN-CIS-016 (the
project-local auditor), PLAN-62 (`manage-run-config`). ⚠ **Re-check against PLAN-46's shipped
surface** (`manage-status/_status_core.py`, `session_binding.py`, `_claude_runtime_impl.py`) before
pairing this with anything touching session binding.

## Dependencies and Sequencing

- Independent; not gated on #1003.
- **Sequence after PLAN-57 if both are queued near each other** — PLAN-57's own spec warns that a
  HYPOTHESIS-heavy surface routes light, and this plan is the most HYPOTHESIS-heavy in the queue.
  Until PLAN-57 lands, expect this plan to be under-routed and **escalate it manually at outline**.

## Notes

- **Largest single lever in the script layer**, per the audit — and the reason it went unnoticed is
  the interesting part, not the number. Worth recording as the epic's clearest example that a
  *truthful* instrument can still leave the dominant fact unreported.
- The reduction half may turn out small or even empty; the observability half (D2) is the durable
  deliverable and should not be dropped if D3 shrinks.

## The budget anchors cannot tell honest scope growth from waste

Message-supplied, HYPOTHESIS until re-verified at outline. **`scope_estimate` token/time budget
anchors do not distinguish honest, gate-driven scope growth from waste.** #1038 is the case in point:
it ran 4M tokens against a `single_module` anchor — **because its D1 gate correctly found 10 sites
where the request named 5, and two were fully broken.** The overrun was the plan working as designed.

⛔ **An anchor that flags both is not a cost signal, it is a noise source** — and worse, it trains
readers to dismiss overruns, which is exactly when a real one goes unexamined. Three of today's
landings (#1034 2.7M, #1037 3.8M, #1038 4M) exceeded their anchors; at that rate the anchor
distinguishes nothing.

⚠ **Coordinate with PLAN-99 (in flight)** — it measures where tokens go, which is the input this
needs to separate discovery cost from waste. **Do not build a second cost derivation**; consume its
output or state plainly that this ships without the discriminator until PLAN-99 lands.

## Inherited Inbox Evidence (folded 2026-07-29 from `truthful-signals-005`)

⭐ **Direct evidence for this plan's thesis, read from an archived plan's own `metrics.md` and
`logs/work.log`** (PLAN-111 / PR #1047), not message-supplied.

| Phase | Dispatched | **Inline main-context** | Tool uses | cache_read |
|---|---:|---:|---:|---:|
| 2-refine | 226,121 | 584,194 | 71 | 21.5 M |
| 3-outline | 405,177 | 944,382 | 122 | 35.0 M |
| 4-plan | 351,392 | 910,954 | 86 | 22.3 M |
| 5-execute | 533,998 | 713,698 | 138 | 57.1 M |
| **6-finalize** | **1,648,020** | **4,960,712** | **429** | **246.3 M** |

⭐ **MARGINAL COST SCALES WITH *WHERE* A STEP RUNS, NOT *WHAT* IT DOES.** Finalize shows 246 M
cache_read across 429 tool uses — on the order of **~0.5 M tokens re-read per tool call**. A
mechanical step late in finalize costs far more than the identical step early, and **nothing in a
per-call view reveals it.**

⇒ **D1 MUST TREAT CONTEXT POSITION AS A FIRST-CLASS COST DIMENSION**, not only call size. This is a
scope correction: a ceiling keyed on call size cannot see that the same call costs ~0.5 M at tool-use
#400 and a fraction at #40.

⚠ **The headline token figure understates the run.** `3,205,944` is the **dispatched accumulator
only**; inline main-context cost is tracked separately and sums to **~8.1 M**, 4.96 M of it in
finalize. ⛔ **Any anchor comparison using the headline compares against a partial figure.**
**UNKNOWN AND MATERIAL: whether the 1.3 M anchor is itself dispatched-only or all-in — establish
before quoting any ratio.**

**The evidence argues AGAINST** "retry refusing bots less" (trades review coverage for cost, treats
the occasion as the cause). **It argues FOR** running retry/verification cycles in a **fresh
envelope** rather than accumulated main context, keeping bounded loop-backs (demonstrably working —
the guard stopped at 3/3), and reducing finalize's own exploration volume (1.88 MB of exploration
result bytes, the largest of any phase).

## Second Evidence Fold (2026-07-29 — `truthful-signals-009`)

`post-merge-review-...-011`: PLAN-102 measured a **~40% token under-report** because the loop-back
**never re-opened the phase metrics window**. ⚠ Shared with **PLAN-CIS-011**, which owns the window
lifecycle — this plan owns the *cost-visibility* consequence, not the window fix. ⛔ Coordinate rather
than duplicating: if PLAN-CIS-011's window fix lands first, re-measure before scoping, because the
under-count this plan is reasoning about may already have changed magnitude.

## Evidence Fold — 2026-07-29, from `truthful-signals-012` item 5

⚠ **Lead, not fact** — re-verify at outline.

**`metrics.md` omits `6-finalize` entirely**, so a plan cannot state its own token cost and no budget
anchor can be applied against a complete figure. PLAN-114 reported 2.2 M tokens across "6/6 phases"
while the table itself omits **the most expensive phase**. ⭐ The "6/6" claim beside an incomplete
table is the confident-total-over-a-partial-population shape — the aggregate is not merely missing a
row, it is *asserting completeness it does not have*.

⚠ **Boundary against PLAN-CIS-011**: PLAN-CIS-011 already carries "close the `6-finalize` metrics row on the
terminal path" as part of its `(k)` step-contract arm, and notes that this is a **call-site omission,
not a missing capability**. This plan owns the **cost-visibility / ceiling** consequence. ⛔ Coordinate
— do not ship two fixes for one omission; if PLAN-CIS-011 lands first, re-measure before scoping.

## Second Evidence Fold — 2026-07-29, `truthful-signals-014` + `-016`

⚠ **Leads, not facts.** Four observations that share **one shape**, which is the reusable part:

- **Three artifacts disagree about one plan's token cost, and one labels a phase sum as the PLAN
  total.** Second sighting across the two batches — so "three different totals, none of them the cost"
  is reproducible, not a one-off.
- On another run **`metrics.md` understated tokens 2.7×**.
- **Three token-accounting artifacts each stop recording at a different time, and none says so.**
- **`execution.toon`'s `execution_log` silently stops recording after a loop-back.**

⭐ **The common shape, and the deliverable this fold argues for: A TRUNCATED RECORD THAT DOES NOT
DECLARE ITS OWN TRUNCATION.** Each artifact is individually defensible — it recorded what it saw — and
collectively they produce three confident, mutually contradictory answers to "what did this plan cost",
with no way for a reader to tell which is complete.

⇒ **This is the same rule PLAN-CIS-012's fold carries, applied to cost rather than footprint**: *an artifact
must state the boundary of what it observed.* ⛔ Scope the fix as **the boundary declaration**, not as
reconciling the three numbers — reconciliation without truncation markers just produces a fourth number.

⚠ **A labelling defect hides inside this**: an artifact that labels a **phase sum** as the **plan total**
is not merely truncated, it is *mis-declared*. Those need separating: one is a missing marker, the other
is a wrong name for a real quantity.

⚠ **Boundary against PLAN-CIS-011 unchanged** — the `6-finalize` row-closing call-site omission is theirs;
this plan owns the cost-visibility and truncation-declaration consequence. The loop-back
`execution_log` stop may be the same seam as their window-reopen work: **coordinate, do not fix twice.**

## Evidence Fold — 2026-08-08, from `lessons-handling-…-003` cluster C08

**`2026-07-26-22-003` — `platform_runtime session` plus the pretooluse hook consume 59% of all recorded
script wall-clock (110k invocations, 4.3h). Per-tool-call subprocess overhead is the corpus's single
largest script cost.**

⭐ **A magnitude claim about a seam nobody would name as a cost centre**, and this plan's per-call-ceiling
thesis is exactly where an aggregate-invisible per-call cost belongs.

⛔⛔ **BUT READ THE DENOMINATOR BEFORE CITING IT — the sender flagged this itself and it is binding.**
The 59% is **wall-clock over script invocations**. This epic's standing, first-party-verified result is
that **~99% of billing weight is CONTEXT, not generation and not wall-clock**. ⇒ **The two are measured
in different currencies and this figure does NOT convert into a token-reduction lever on its own.**

- **OBSERVED-about-wall-clock**: the 59% share, as the lesson recorded it, over its own unpublished
  population (110k invocations / 4.3h — quoted, not re-derived).
- **HYPOTHESIS-about-cost**: that this seam is a material share of *billed* cost. **Unverified, and it is
  the claim that would matter.**

⇒ ⛔ **Do not cite this as a token lever without first restating it against the billing composition.**
A wall-clock share re-quoted as a cost share is precisely the partition-quoted-as-a-whole archetype this
epic exists to catch — and the sibling epic already committed exactly that error once, one section after
writing the rule against it. ⭐ **If the restatement shows the seam is cheap in tokens and expensive in
seconds, that is still a real and reportable finding** — it is just an operator-latency finding, not a
priority-one billing one. Say which.

**Claim labels** — OBSERVED: lesson id, component, category; the currency mismatch above.
HYPOTHESIS (verify-at-outline): the seam's share of *billed* cost. Confirm/refute artifact: the
per-invocation context cost of `platform_runtime session` against `work/metrics.toon`'s billing-weighted
fields — not against the script wall-clock ledger, which is the source of the mismatch.

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
