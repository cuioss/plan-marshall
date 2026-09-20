envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-09-03T11:34:36Z

## A letter-suffixed spec loses its suffix, and three specs collapse onto one `plan_id`

**Transfer, not an offer.** Routed to `truthful-signals` under the three-way rule: the subject is the
epic-spec parser and the `corpus surfaces` payload, not the PR-review apparatus. Removed from
`review-apparatus`'s work; that ledger keeps the derivation record and one local workaround.

### What was observed

Found first-party during a `review-apparatus` cleanup re-grounding pass, 2026-09-03, at HEAD
`19453cb1b`:

```
corpus surfaces --slug review-apparatus
  PLAN-PR-025 <- PLAN-PR-025-a-refusal-is-recorded-as-a-refusal-and-the-contract-says-so.md   (retired)
  PLAN-PR-025 <- PLAN-PR-025A-a-refusal-is-recorded-as-a-refusal-the-record.md                (shipped #1368)
  PLAN-PR-025 <- PLAN-PR-025B-arm-the-refusal-recovery-that-has-never-run.md                  (staged)
```

Three distinct specs, three distinct queue rows, one derived `plan_id`.

### Why it matters

`corpus surfaces`'s flat `claimed[]` list keys by `plan_id`. So the declared paths of a **staged,
emittable** spec are merged with those of a **retired** one and a **shipped** one under one key, and
a consumer looking up `claimed[]` for `PLAN-PR-025B` finds no rows at all — **silence, not an empty
surface**, which is the exact distinction ADR-019 exists to preserve.

⭐ It bit immediately and observably: this pass's intersection sweep scored `PLAN-PR-025B` at `0/0`
declared paths moved, and would have recorded it as undisturbed. Its declared surface actually
contains `.plan/marshal.json`, which **did** move in the window. A wrong "undisturbed" verdict on a
spec that is next in the emit queue.

### Scope it correctly — the write path is FINE

⛔ Do not widen this into "the 025 family is unaddressable". Two of three surfaces are correct:

| Surface | Status |
|---|---|
| `corpus set-verdict --plan PLAN-PR-025B` | **correct** — resolves via `_spec_matches_row` (`orchestrator.py:1119`), `path.stem == plan_id or path.stem.startswith(f'{plan_id}-')`, which matches uniquely |
| the per-spec `corpus surfaces` ROW | **correct** — keys by `spec` filename; reports 025B `declarative`, `claimed_count: 5`, `admits_disjointness_check: true` |
| the derived `plan_id` field, and `claimed[]` keyed on it | ⛔ **wrong** — suffix dropped |

### Root cause

A grammar gap. The documented plan-id forms (`orchestrator inbox detect`) all require **trailing
digits**: `PLAN-{DIGITS}`, `PLAN-{SLUG}-{DIGITS}`, `{SLUG}-{DIGITS}`. The letter-suffixed
`025A`/`025B` naming was invented by `review-apparatus`'s own mandatory 025 split and never taught to
the parsers, so id derivation stops at the digit run and drops the suffix.

⇒ The decision is not only "fix the regex". It is **whether letter suffixes are a legal plan-id form
at all**. Either extend the grammar in its single detection seam and everything that derives an id
from a spec filename, or rule the form out and rename — ⛔ but renaming is barred for a launched or
shipped plan, and `PLAN-PR-025A` is already shipped, so the rule-out arm cannot be applied
retroactively. That asymmetry is the decision, and it is why this is a spec rather than a patch.

### Labels

- OBSERVED: the three-way collapse, read from a live `corpus surfaces` payload.
- OBSERVED: `_spec_matches_row` at `orchestrator.py:1119` matches the suffixed stem correctly.
- OBSERVED: the three accepted id forms all require trailing digits (`inbox detect` § grammar table).
- HYPOTHESIS: other letter-suffixed specs exist elsewhere in the store. ⛔ **NOT checked** — only
  `review-apparatus` was swept. Do not report a population without deriving it.

### Suggested shape (not a prescription)

Derive the id from the queue row rather than re-parsing the filename wherever a row is already in
hand, and where a filename must be parsed, extend the single detection seam rather than adding a
second parser. ⛔ A matched negative control is required: a spec whose id genuinely has no suffix
must still resolve unchanged, or a dropped suffix is merely replaced by a spurious one.
