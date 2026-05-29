# Check: pr-merge-velocity

Computes each archived plan's PR open-to-merge duration and flags plans with
long review cycles. The deterministic extraction lives in `scripts/audit.py`;
this sub-document is the interpretation guide.

## Inputs the check reads

Per scanned plan, the script reads the CI/PR run artifacts under
`artifacts/ci-runs/*/manifest.toon`. From each manifest it extracts the
`pr_number` and the `fetched_at` timestamp. Across all of a plan's CI-run
manifests it takes the earliest `fetched_at` as the open-side reference and the
latest as the merge-side reference, computing the elapsed duration between them.

Timestamps are parsed as ISO-8601 UTC (`YYYY-MM-DDTHH:MM:SS`) using only the
standard library — no third-party timezone dependency.

## Not-applicable handling

A plan with no PR artifact — no `pr_number`, or no parseable open/merge
timestamps — is reported with `applicable: false` and empty velocity columns. It
is **not** flagged. Local-only plans and plans whose CI artifacts were never
persisted land here.

## Threshold

A plan is flagged (`flagged: true`) when its open-to-merge elapsed duration
exceeds 24 hours. Otherwise `flagged` is empty.

## Emitted columns

```
rows[N]{plan_id,pr_number,elapsed_hours,flagged,applicable}
```

| Column | Meaning |
|--------|---------|
| `plan_id` | The scanned plan's directory basename. |
| `pr_number` | The PR number from the CI manifest (empty when not applicable). |
| `elapsed_hours` | Open-to-merge duration in hours, one decimal (empty when not applicable). |
| `flagged` | `true` when the cycle exceeds 24h; otherwise empty. |
| `applicable` | `true` when a PR artifact with parseable timestamps was found; otherwise `false`. |

## How the orchestrator interprets the rows

- **`applicable: false`** — no PR data; skip the plan for this check. Not a
  defect.
- **`flagged` empty, `applicable: true`** — the review cycle was within the
  threshold; informational `elapsed_hours` for trend context.
- **`flagged: true`** — the PR sat open longer than the threshold. Surface it as
  a review-velocity signal. A single slow cycle is informational; a recurrence
  across the corpus is a candidate systemic signal worth cross-reading with the
  recurring-pattern detector.
- The `elapsed_hours` derived from `fetched_at` timestamps is a proxy for the
  true open-to-merge window (it spans the first to last CI artifact fetch).
  Treat near-zero values as "single-fetch plan" rather than "instant merge".

## Critical rules

- The script is the single source of truth for the velocity rows and the
  threshold. Do not re-extract timestamps in chat.
- This check is read-only; it never edits `.plan/` files.
