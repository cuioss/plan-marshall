# Check: recurring-pattern-detector (cross-plan)

Aggregates findings across all scanned archived plans and surfaces any finding
signature appearing in N or more plans as a systemic signal. This is a
cross-plan check — it emits aggregate rows over the whole corpus rather than one
row per plan. The deterministic aggregation lives in `scripts/audit.py`; this
sub-document is the interpretation guide.

## Inputs the check reads

For every scanned plan, the script reads `artifacts/findings/*.jsonl` and
derives a finding **signature** from each row: the row's `title` (or `type` when
`title` is absent), truncated at the first `:` and lowercased so that
plan-specific suffixes (e.g. `phase-5-step-missing-role-field: operations.md`)
collapse to a shared signature (`phase-5-step-missing-role-field`). Each
signature is counted once per plan (a signature appearing in multiple findings
within one plan still contributes a single occurrence for that plan).

## Threshold

A signature is reported as systemic when it appears in **N ≥ 3 plans** (the
3-or-more systemic threshold from the request, exposed as `threshold` in the
emitted block). Signatures below the threshold are not emitted.

## Emitted columns

```
threshold: 3
systemic_count: M
rows[M]{signature,occurrence_count,plan_ids}
```

| Column | Meaning |
|--------|---------|
| `signature` | The collapsed finding signature (title prefix, lowercased). |
| `occurrence_count` | Number of distinct plans the signature appears in. |
| `plan_ids` | `;`-joined plan ids contributing to the signature. |

Rows are ordered by descending `occurrence_count`, then by signature.

## How the orchestrator interprets the rows

- Each systemic row is a **candidate lesson-filing input**: a finding recurring
  across 3+ plans is a systemic signal, not a one-off. The orchestrator feeds
  the signature into the three-gate `lesson-creation-policy.md` sequence (dedup
  → active-plan check → create) documented in the SKILL.md orchestration Step 4.
- A high `occurrence_count` strengthens the case that the underlying issue is
  structural and warrants a lesson (or extending an existing one via Gate 1's
  `merge_into`).
- Generic signatures (e.g. broad source/type buckets) may appear with high
  counts without representing an actionable systemic defect — apply judgement
  before filing; the three-gate policy's dedup and active-plan gates are the
  backstop.

## Critical rules

- The script is the single source of truth for the aggregate rows and the
  signature-collapsing rule. Do not re-aggregate findings in chat.
- Systemic signals always pass through the three-gate policy before any lesson
  is filed — the 3+ threshold gates which signatures become candidates, not
  whether they are filed.
- This check is read-only; it never edits `.plan/` files.
