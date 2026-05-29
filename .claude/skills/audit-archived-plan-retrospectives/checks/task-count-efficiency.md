# Check: task-count-efficiency

Counts each archived plan's `tasks/TASK-*.json` files and flags outliers
relative to the plan's deliverable count — under-decomposed (too few tasks) or
over-decomposed (too many). The deterministic counting lives in
`scripts/audit.py`; this sub-document is the interpretation guide.

## Inputs the check reads

Per scanned plan, the script:

- Counts the `tasks/TASK-*.json` files in the plan directory.
- Resolves the deliverable count from `references.json::deliverables` when
  present, falling back to the distinct `deliverable` ids referenced across the
  plan's `TASK-*.json` files.

## Outlier rule

The check computes the tasks-per-deliverable ratio and flags it when outside the
expected band:

| Direction | Condition | Reported as |
|-----------|-----------|-------------|
| Under-decomposed | ratio < 0.5 | `under_decomposed (ratio={r})` |
| Over-decomposed | ratio > 4.0 | `over_decomposed (ratio={r})` |

A plan with zero deliverables (no `references.json` deliverables and no
deliverable ids on its tasks) is not flagged — the ratio is undefined.

## Emitted columns

```
rows[N]{plan_id,task_count,deliverable_count,outlier}
```

| Column | Meaning |
|--------|---------|
| `plan_id` | The scanned plan's directory basename. |
| `task_count` | Number of `TASK-*.json` files. |
| `deliverable_count` | Resolved deliverable count. |
| `outlier` | Empty when the tasks-per-deliverable ratio is inside the band; otherwise the under-/over-decomposed verdict with the ratio. |

## How the orchestrator interprets the rows

- **`outlier` empty** — the task decomposition was proportionate to the
  deliverable count; no action.
- **`under_decomposed`** — fewer tasks than deliverables warrant. The plan may
  have bundled multiple deliverables into single tasks, reducing per-task
  verification granularity. Surface it as a planning-granularity signal.
- **`over_decomposed`** — many more tasks than deliverables. The plan may have
  fragmented work into excessive micro-tasks, inflating dispatch overhead.
  Surface it; cross-read with `token-efficiency-trend` since over-decomposition
  often correlates with higher tokens-per-phase.
- Recurring outliers in one direction across the corpus are a candidate systemic
  signal — cross-read with the recurring-pattern detector before filing a
  lesson.

## Critical rules

- The script is the single source of truth for the counts and the outlier band.
  Do not re-count tasks or re-derive the ratio in chat.
- This check is read-only; it never edits `.plan/` files.
