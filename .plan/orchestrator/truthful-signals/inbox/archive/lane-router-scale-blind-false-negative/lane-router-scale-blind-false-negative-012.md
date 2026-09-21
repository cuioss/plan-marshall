envelope_version=1
sender_type=plan
sender_id=lane-router-scale-blind-false-negative
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T19:18:07Z

component=plan-marshall:manage-metrics
category=bug
bundle=plan-marshall

# One phase, three token totals, 6x apart — and every artifact presents its number as complete

Phase 6 of this plan has three first-party records of how many tokens it consumed:

| Artifact | Value | Population |
|---|---:|---|
| `work/metrics-accumulator-6-finalize.toon` | **2,639,930** | `samples: 12` |
| `execution.toon` → `execution_log` (finalize rows) | **2,021,623** | 8 token-bearing rows of 19 |
| `work/metrics-dispatch-boundaries-6-finalize.toon` | **439,771** | `rows: 3` |

A **6x spread** on a single quantity. None of the three carries a partial marker, a sample
count the reader is expected to check, or any indication that a sibling artifact disagrees.

The downstream consequences are already visible in this run:

- **`check-routing-decisions` reports `cost_preview.actual_tokens: 2021623`** — the middle
  number — with `predicted_tokens: null` and no caveat. Any posture-calibration decision
  taken from that figure is 24% low.
- **The retrospective's own `DISPATCH_TERMINATION_CAUSE` rule** reads the dispatch-boundaries
  file as its population. It graded a 12-dispatch phase from 3 rows and would have reported
  a clean per-cause distribution over 25% of the data.
- **`metrics.md`** was generated at phase-6 *entry* and prints `> Partial: unrecorded phases
  — 6-finalize`. The operator-facing phase breakdown omits the largest phase of the plan
  entirely — the one honest artifact of the four, and the one that shows nothing.

Separately, **7 of 19 `execution_log` rows record `total_tokens=0, tool_uses=0,
duration_ms=0`** (`sync-baseline`, `pre-push-quality-gate`, `architecture-refresh`, `push`,
`era-stamp-fill`, `ci-verify`, `branch-cleanup`). These are inline steps, so "no dispatch
boundary was recorded" is being written as "this step cost nothing". `ci-verify` alone
spanned a 547-second `ci_complete_precondition` call and is logged as zero duration. And
**2 steps that reached `outcome=done` on `status.metadata.phase_steps`**
(`project:finalize-step-review-retrospective`, `lessons-capture`) **have no `execution_log`
row at all** — the manifest's log and the status step map disagree about which steps ran.

## Solution

- **Add `manage-metrics reconcile --plan-id X`**: emit per-artifact totals plus an explicit
  disagreement flag. Today every consumer picks one artifact and reports a confident number;
  nothing in the system can currently notice the disagreement.
- **Make every partial record say so.** An artifact with `samples: 12` whose sibling holds 3
  rows must not render as a total. Carry the expected population alongside the observed one,
  and refuse to report a sum whose population is short.
- **Distinguish "inline, not separately measured" from "zero".** A `total_tokens=0` row
  should be `null`/`not_measured`, not `0` — a zero is an assertion.
- **Regenerate `metrics.md` at plan close**, not at phase-6 entry, so the breakdown the
  operator reads includes finalize.

## Impact

Every plan. Any cost-calibration, lane-lever, or token-economics conclusion drawn from plan
artifacts is currently drawn from an arbitrary one of three disagreeing numbers. This is the
`truthful-signals` theme in its purest measurable form: not a wrong verdict, a **confident
number whose population is undisclosed**.
