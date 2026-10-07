# Token-Usage Aggregates & Distribution

Corpus: **58 plans** (8 archived, 49 dormated, 1 TokenSheriff source). Ratio stats computed over the **51 fully-recorded plans with known LOC** (partial-metrics plans excluded so the floor under-counts don't skew ratios).

## Corpus-confidence caveat

Beyond the partial-metrics exclusion above, two corpus-wide leaks mean the headline figures are **floors with unquantified error**, not point estimates: (a) pre-#912 harness background-kills (~90 across a 23-day window) were absorbed as idle/wall time with zero trace, so wall/idle figures for that era under-state re-run cost (made legible going forward by #912, not back-filled); and (b) dispatched-phase Totals historically under-counted because the phase total was never reconciled against the dispatch-boundaries sum (fixed by the dispatch-boundary reconciliation, PR #922; pre-fix rows read low). The `unrecorded_phases`-only caveat does not cover either leak.

## Corpus totals

- Total generation tokens across corpus: **125,701,085** (partial-metrics plans under-count, so this is itself a floor).
- Per-plan total tokens (fully-recorded plans): median **1,908,547**, min **1,034,469**, max **4,193,249**
- The **fixed-overhead floor**: the cheapest fully-recorded plan cost **1,034,469** tokens for **20 LOC** (`fix-escalate-ask-guard-ordering`). No fully-recorded plan in the corpus — including ≤50-LOC one-line fixes — landed for under ~1.0M tokens. (The partial-metrics `ci-pr-safe-merge` shows 938,092 but its 6-finalize tokens are unrecorded, so its true total is higher.)

## tokens-per-LOC (the efficiency question)

- Median **3,504** tok/LOC, min **418**, max **94,715** — a **227x** spread.
- The ratio is driven almost entirely by LOC, not by plan complexity: small changes pay the same fixed framework overhead spread over fewer lines.

| LOC bucket | n | median total tok | median tok/LOC |
|------------|---|------------------|----------------|
| 0–50 LOC | 6 | 1,648,573 | 57,650 |
| 51–200 | 9 | 1,444,672 | 9,799 |
| 201–800 | 13 | 1,909,490 | 4,946 |
| 801–2000 | 13 | 2,463,961 | 1,976 |
| >2000 | 10 | 2,921,344 | 939 |

## By change-type

| change-type | n | median total tok | median LOC | median tok/LOC |
|-------------|---|------------------|------------|----------------|
| tech_debt | 10 | 2,248,939 | 1,434 | 2,013 |
| feature | 23 | 2,171,802 | 1,119 | 2,916 |
| bug_fix | 14 | 1,712,904 | 137 | 9,432 |
| enhancement | 3 | 1,641,463 | 951 | 1,777 |
| analysis | 1 | 1,590,319 | 245 | 6,491 |

## By scope

| scope | n | median total tok | median LOC | median tok/LOC |
|-------|---|------------------|------------|----------------|
| multi_module | 20 | 2,390,165 | 1,040 | 2,636 |
| single_module | 22 | 1,872,449 | 709 | 2,828 |
| surgical | 9 | 1,387,939 | 125 | 9,205 |

## Per-phase corpus token share (where each token is spent)

| phase | corpus tokens | share |
|-------|---------------|-------|
| 1-init | 3,603,453 | 2.9% |
| 2-refine | 7,361,522 | 5.9% |
| 3-outline | 20,467,450 | 16.3% |
| 4-plan | 13,533,835 | 10.8% |
| 5-execute | 34,467,523 | 27.4% |
| 6-finalize | 46,267,302 | 36.8% |
| **planning (init→plan)** | 44,966,260 | 35.8% |
| **execute** | 34,467,523 | 27.4% |
| **finalize** | 46,267,302 | 36.8% |
