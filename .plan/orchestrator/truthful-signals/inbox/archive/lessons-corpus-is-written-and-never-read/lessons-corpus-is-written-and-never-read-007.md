envelope_version=1
sender_type=plan
sender_id=lessons-corpus-is-written-and-never-read
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T19:26:10Z

component=plan-marshall:manage-metrics
category=bug
created=2026-07-28

# `metrics.md` renders the largest-token phase as unrecorded, under-reporting the plan by 36%

`metrics.md` for this plan reports:

- `6-finalize` row: every column `-`
- Header caveat: `> Partial: unrecorded phases — 6-finalize`
- Total: `1,467,645 (n=4/6)`

The tokens are not missing. `logs/decision.log` carries seven
`(plan-marshall:manage-execution-manifest:record-step)` lines with explicit
`total_tokens=` values for the finalize steps that dispatched:

| step | tokens |
|---|---:|
| lessons-housekeeping | 118,499 |
| plugin-doctor | 96,092 |
| pre-submission-self-review | 237,568 |
| finalize-simplify | 88,043 |
| create-pr | 89,752 |
| review-retrospective | 88,089 |
| lessons-capture | 121,358 |
| **sum** | **839,401** |

Real plan total is therefore ≈ **2,307,046** tokens, of which 6-finalize is the
single largest phase at 36%. `check-routing-decisions` independently computes the
same 839,401 as its `cost_preview.actual_tokens`, so the number is already
derivable inside the toolchain — it simply never reaches `metrics.md`.

## Why this is a truthfulness defect, not a cosmetic gap

The budget anchors in `plan-efficiency.md` for a `single_module + feature` plan
are: warning ≥1.0M tokens / ≥75 min, **error ≥1.6M / ≥120 min**. Reading
`metrics.md` alone (1.47M) trips only the warning. Reading the real total (2.31M
over 213 min wall-clock) trips **both error anchors**. The artifact whose entire
purpose is token accounting is the artifact that hides the over-budget signal.

The `n=4/6` caveat is honest about *coverage* but the emitted `**Total**` is
still a bare number a reader will quote.

## Root cause

Finalize-step token capture depends on dispatch-boundary records, and the phase
writes `metrics.md` before/without folding in the `record-step` entries. Nine of
the sixteen finalize steps additionally record `total_tokens=0` — those zeros mean
"inline step, no dispatch boundary", not "this step was free", and they are
indistinguishable from real zeros in the same field.

## Solution

1. Add a recovery pass (`manage-metrics` verb) that sums the `record-step`
   decision entries into the `6-finalize` row before the report is rendered.
2. Distinguish `0` (measured zero) from `null`/`n/a` (inline, unmeasured) in the
   per-step token field, so the phase total can state its own coverage.
3. Until the row is populated, the `**Total**` line should not print a bare
   summable figure for a partial population — the `(n=4/6)` annotation belongs
   inside the number's own presentation, which it currently is, but the row-level
   `-` gives no hint that 839K is recoverable two files away.
