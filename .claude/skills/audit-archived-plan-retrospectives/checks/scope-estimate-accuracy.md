# Check: scope-estimate-accuracy

Compares each archived plan's declared `references.json::scope_estimate` against
the realized footprint's file count and flags mismatches. The deterministic
comparison lives in `scripts/audit.py`; this sub-document is the interpretation
guide.

## Inputs the check reads

Per scanned plan, the script reads `references.json`:

- `scope_estimate` — the declared scope band (`surgical`, `single_module`,
  `multi_module`).
- The actual touched-file count — the cardinality of the **realized footprint**,
  resolved through the shared resolver's tier order rather than read off any
  single key. The first tier that answers decides:

  1. `realized_footprint` — the capture-while-true set written by
     `default:branch-cleanup` while the worktree still existed.
  2. `merge_commit_sha` — the landing commit's own first-parent range
     (`{sha}^1..{sha}`), which names exactly what that commit introduced for both
     a squash landing and a true merge.
  3. `modified_files` — the retired legacy key, kept as the LAST tier for
     archived plans written before it stopped being emitted.

  ⛔ A tier that answers with an **empty** set has resolved the footprint: the
  plan changed nothing, and the count is a real `0`. That is a different answer
  from **no tier resolving at all**, and only in the latter case does the check
  fall back to the declared `affected_files` (planned). The distinction is
  load-bearing — reading the raw `modified_files` key first, or treating a
  resolved-empty footprint as absent, silently grades a plan on what it *planned*
  to touch instead of on what it *did*.

**Corpus partition (delivery-cost check).** This check runs over the SHIPPING
partition of the corpus, not every scanned plan: a plan carrying no delivery
evidence — no PR record and no footprint — is excluded before the check sees it.
See SKILL.md § "Shipping-predicate corpus partition" for the derived predicate.

## Scope-band mapping

Each declared scope maps to an inclusive expected file-count band. A plan whose
actual file count falls outside its declared band is flagged:

| Declared scope | Expected file band |
|----------------|--------------------|
| `surgical` | 1–3 files |
| `single_module` | 1–15 files |
| `multi_module` | 5+ files (no upper bound) |

A declared scope with no band mapping (or an empty declaration) is reported with
a note rather than a hard mismatch.

## Emitted columns

```
rows[N]{plan_id,declared_scope,actual_file_count,mismatch}
```

| Column | Meaning |
|--------|---------|
| `plan_id` | The scanned plan's directory basename. |
| `declared_scope` | The `scope_estimate` declared in `references.json` (empty when unset). |
| `actual_file_count` | The realized footprint's cardinality, resolved through the `realized_footprint` → `merge_commit_sha` → `modified_files` tier order; the declared `affected_files` count only when no tier resolves. |
| `mismatch` | Empty when the actual count is inside the declared band; otherwise `declared={scope} band=[{low},{high}] actual={n}`. |

### Corpus-partition exclusion columns

Two block-header lines accompany the rows above:

| Line | Meaning |
|------|---------|
| `plans_excluded_non_shipping` | How many scanned plans were excluded from this check's corpus as non-shipping — a number reported SEPARATELY from the examined count. |
| `excluded_non_shipping_plan_ids` | The excluded plans, each as `{plan_id}:{archived_reason or unrecorded}`. |

An excluded plan delivered nothing, so it is absent from this check's aggregates
by design; the count is the audit trail proving no row was silently dropped.

## How the orchestrator interprets the rows

- **`mismatch` empty** — the declared scope matched the realized footprint; no
  action.
- **`mismatch` non-empty, actual > band** — the plan was under-estimated (e.g.
  `surgical` declared but many files changed). This is the more common
  direction and signals that the refine/outline scope estimate ran low; surface
  it as a planning-accuracy signal.
- **`mismatch` non-empty, actual < band** — the plan was over-estimated (e.g.
  `multi_module` declared but a single file changed), or the realized footprint
  collapsed during execution. Surface it; a plan that consistently over-declares
  scope may indicate a conservative estimator.
- Recurring mis-estimates across the corpus are a candidate systemic signal —
  cross-read with the recurring-pattern detector before filing a lesson.

## Critical rules

- The script is the single source of truth for the band mapping and the
  mismatch verdict. Do not re-derive the bands in chat.
- This check is read-only; it never edits `.plan/` files.
