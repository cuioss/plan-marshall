# Check: quality-verification-report

Surfaces, per archived plan, which findings were present, which lessons were
proposed, and whether each proposed lesson was already filed. The deterministic
parsing lives in `scripts/audit.py`; this sub-document is the interpretation
guide for the emitted rows.

## Inputs the check reads

Per scanned plan, the script reads:

- `quality-verification-report.md` — the retrospective report at the plan root.
  It parses every embedded ```json``` block and sums each block's `findings[]`
  array, and collects any `proposed_lessons[]` / `lessons[]` entries (a
  proposed lesson's signature is its `title` / `signature` / `detail`).
- `artifacts/findings/*.jsonl` — the per-phase Q-Gate / assessment / PR-comment
  findings stores. Each JSONL row counts toward `findings_present`.

The filed/unfiled cross-check compares each proposed-lesson signature against
the lessons corpus at `.plan/local/lessons-learned/*.md` (matching on the first
markdown heading or `title:` frontmatter of each lesson, case-insensitive,
substring either direction). A proposed lesson whose signature matches an
existing lesson is treated as already filed and excluded from
`unfiled_lessons`.

## Emitted columns

```
rows[N]{plan_id,findings_present,proposed_lessons,unfiled_lessons,unfiled_signatures}
```

| Column | Meaning |
|--------|---------|
| `plan_id` | The scanned plan's directory basename. |
| `findings_present` | Total findings across the report's JSON blocks plus the `artifacts/findings/*.jsonl` rows. |
| `proposed_lessons` | Count of proposed-lesson signatures found in the report. |
| `unfiled_lessons` | Count of proposed lessons whose signature did NOT match any existing lesson in the corpus. |
| `unfiled_signatures` | The `;`-joined signatures of the unfiled proposed lessons. |

## How the orchestrator interprets the rows

- **`findings_present` only** — informational; a high finding count is not a
  defect by itself, but a plan with many findings and zero proposed lessons may
  indicate the retrospective under-captured systemic signals.
- **`unfiled_lessons > 0`** — the report proposed lessons that were never filed.
  Each entry in `unfiled_signatures` is a **candidate lesson-filing input**: the
  orchestrator feeds it into the three-gate `lesson-creation-policy.md` sequence
  (dedup → active-plan check → create) documented in the SKILL.md orchestration
  Step 4. The filed/unfiled cross-check here is a pre-filter, not a substitute
  for Gate 1 — Gate 1's dedup still runs because the corpus match here is a
  coarse substring heuristic.
- **`unfiled_lessons == 0`** — every proposed lesson is already covered in the
  corpus; no filing action. A signature this check marks as filed MUST NOT be
  re-filed.

## Critical rules

- The script is the single source of truth for the surfaced rows. Do not
  re-parse the report or the findings stores in chat.
- The corpus cross-check is a coarse substring heuristic; it suppresses obvious
  duplicates but the authoritative dedup is Gate 1 of the three-gate policy.
- This check is read-only; it never edits `.plan/` files or the lessons corpus.
