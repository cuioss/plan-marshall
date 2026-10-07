envelope_version=1
sender_type=plan
sender_id=manage-lessons-mixes-local-time-and-utc
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T18:07:40Z

component=plan-marshall:manage-metrics
category=bug
created=2026-07-29

# Three different "total token" signals for one plan, all partial, none of them the plan's cost

This surgical bug-fix plan produced three authoritative-looking totals, and no surface reconciles them:

| Surface | Value | What it actually covers |
|---|---|---|
| `metrics.md` **Total** row | **741,774** | phases 2/4/5 only (`n=3/6`), generated 14:57Z — before all of finalize and before the loop-back re-execute |
| `check-routing-decisions` `cost_preview.actual_tokens` | **540,163** | the six `execution_log` finalize rows only — the exact complement of the metrics.md figure |
| reconstructed from dispatch boundaries + execution log | **~1,430,628** | phases 2/4/5 + the second 5-execute envelope (148,691) + finalize (540,163) |

The two emitted numbers are *disjoint slices of the same plan*, each labelled as a total. Neither is close to the real spend; `metrics.md` understates it by **48%**.

## Why the `n=3/6` marker is not sufficient

`metrics.md` does carry `(n=3/6)` and a "Partial: unrecorded phases — 6-finalize" note, which is honest as far as it goes. But:

- the note names only `6-finalize`, while the row is also missing the **loop-back second execute envelope** (148,691 tokens) that landed after the file was generated. The file cannot know it went stale, and nothing regenerates it.
- `cost_preview.actual_tokens` carries **no partiality marker at all** — the field name asserts it is the actual cost.

## Cost context, since it is the number a budget check would read

Against the `surgical + bug_fix` anchor (warning 500K, error 800K), the reconstructed 1.43M crosses the **error** column by 79%, and finalize alone (540K) outspent the entire fix-and-test phase (373K). A budget check reading `metrics.md` sees 741,774 — under the error anchor — and passes.

## Solution

- Regenerate or invalidate `metrics.md` at the end of finalize rather than at the 5→6 transition, and make loop-back re-entry invalidate a previously written metrics file.
- Rename `cost_preview.actual_tokens` to name its scope (`finalize_execution_log_tokens`) or widen it to the whole plan; a field called `actual_tokens` must not be a phase slice.
- Any partial total must carry its own coverage denominator in the same field, not in adjacent prose.

## Impact

Every budget/efficiency judgement made from these artifacts — including this retrospective's own plan-efficiency aspect, and any cross-plan token-economics audit — is reading one of two disjoint half-totals presented as wholes.
