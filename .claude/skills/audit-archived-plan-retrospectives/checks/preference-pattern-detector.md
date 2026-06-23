# Check: preference-pattern-detector (cross-plan)

Aggregates recurring user gate-dispositions across all scanned archived plans and
surfaces any `(module, finding-class, disposition)` tuple appearing in N or more
distinct plans as a candidate preference. This is a cross-plan check — it emits
aggregate rows over the whole corpus rather than one row per plan. The
deterministic aggregation lives in `scripts/audit.py`; this sub-document is the
interpretation guide.

## Inputs the check reads

For every scanned plan, the script reads `artifacts/findings/*.jsonl` and, for
each finding carrying a **user-gate disposition**, derives a
`(module, finding-class, disposition)` tuple:

- **disposition** — the finding's `resolution` field narrowed to the three
  user-gate dispositions: `suppressed`, `accepted`, `taken_into_account`.
  Findings with any other `resolution` (e.g. `fixed`, `pending`) or a `promoted`
  marker are not preferences and are excluded.
- **finding-class** — the same collapsed signature the recurring-pattern detector
  uses: the row's `title` (or `type` when `title` is absent), truncated at the
  first `:` and lowercased.
- **module** — the finding's `module` attribution, falling back to `component`,
  then to the cross-cutting `default` bucket when neither is present.

Each tuple is counted once per plan (a tuple appearing in multiple findings
within one plan still contributes a single occurrence for that plan).

## Threshold

A tuple is surfaced as a candidate preference when it appears in **N ≥
`THRESHOLDS["preference_disposition_occurrences"]` plans** (default 3, mirroring
the recurring-pattern systemic band; exposed as `threshold` in the emitted
block). Tuples below the threshold are not emitted. The threshold gate is owned
by the script's `THRESHOLDS` constant — meta-only; consumers cannot edit it. (The
consumer-available per-plan emitter gates via its own `marshal.json` knob; see
the shared contract below.)

## Emitted columns

```
threshold: 3
candidate_count: M
rows[M]{module,finding_class,disposition,occurrence_count,plan_ids,severity}
```

| Column | Meaning |
|--------|---------|
| `module` | The finding's module attribution (or `default` for cross-cutting). |
| `finding_class` | The collapsed finding signature (title prefix, lowercased). |
| `disposition` | The user-gate disposition (`suppressed`/`accepted`/`taken_into_account`). |
| `occurrence_count` | Number of distinct plans the tuple appears in. |
| `plan_ids` | `;`-joined plan ids contributing to the tuple. |
| `severity` | Always `genuine` — every surfaced row cleared the threshold. |

Rows are ordered by descending `occurrence_count`, then by `module`,
`finding_class`, `disposition`.

## How the orchestrator interprets the rows

Each candidate row is a **preference-enrichment input** routed to
`architecture enrich`. Because every surfaced row is already threshold-gated by
the script, SKILL.md Step 4c routes EVERY surfaced row — there is no further
gating in the LLM body. The generalization rule (tuple → best-practice / insight
string), the routing targets (`architecture enrich best-practice` for
module-attributed patterns, `enrich insight --module default` for cross-cutting
patterns), and the "generalize, do not log raw dispositions" privacy invariant
are owned ONCE by
[`phase-6-finalize/standards/disposition-to-hint-routing.md`](../../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/disposition-to-hint-routing.md);
this check does not restate them.

## Dormation note

This is a cross-plan check that participates automatically in the auditor's
existing learn-then-dormate corpus sweep. Dormation operates at the PLAN level
(SKILL.md Step 5 dormates each reviewed plan after ALL checks run), not
per-check, so the existing single-pass learn-then-dormate behavior already covers
this new check — no separate dormation wiring or new dormation code is added.

## Critical rules

- The script is the single source of truth for the aggregate rows, the tuple
  derivation, and the threshold gate. Do not re-aggregate dispositions in chat.
- This check is read-only; it never edits `.plan/` files.
- **Generalize, do not log raw dispositions** — when routing surfaced rows to
  `architecture enrich`, never persist per-finding hash IDs or raw disposition
  rows; persist only the generalized hint string per the shared contract.
