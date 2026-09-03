# Check: preference-pattern-detector (cross-plan)

Aggregates recurring user gate-dispositions across all scanned archived plans and
surfaces any `(module, finding-class, disposition)` tuple appearing in N or more
distinct plans as a candidate preference. This is a cross-plan check — it emits
aggregate rows over the whole corpus rather than one row per plan. The
deterministic aggregation is APPLIED by `scripts/audit.py`; the
authorship-admissibility rule it applies is IMPLEMENTED once elsewhere, in
`manage-findings/scripts/_preference_admissibility.py`, which the script
delegates to. This sub-document is the interpretation guide.

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
  then to the `default` bucket when neither is present. A tuple in the `default`
  bucket is UNATTRIBUTED (see § "Attribution and authorship gates").

Each tuple is counted once per plan (a tuple appearing in multiple findings
within one plan still contributes a single occurrence for that plan).

## Attribution and authorship gates

Two gates run over the derived tuples, both owned by the shared contract
[`phase-6-finalize/standards/disposition-to-hint-routing.md`](../../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/disposition-to-hint-routing.md)
(§§ (d), (e)):

- **Authorship admissibility (pre-count).** A `pr-comment` finding seeds a
  recurrence ONLY when it carries a recognized reviewer `bot_kind`. A `pr-comment`
  with no `bot_kind` is the pipeline's own control traffic (or an unattributed
  comment) and is dropped before counting — self-authored comments cannot become
  evidence about the pipeline's own preferences. Non-comment findings are
  unaffected.
- **Attribution gate (post-count).** A tuple whose module resolves to the
  `default` fallback bucket is UNATTRIBUTED **on this preference-aggregation path** —
  not a cross-cutting judgement here — and is
  **never surfaced as a candidate** — promoting it would route an unverified hint
  to the widest blast radius. Such tuples are tallied in
  `unattributed_excluded_count` so the decision is visible rather than silent.

## Threshold

A tuple is surfaced as a candidate preference when it appears in **N ≥
`THRESHOLDS["preference_disposition_occurrences"]` plans** (default 3, mirroring
the recurring-pattern systemic band; exposed as `threshold` in the emitted
block). Tuples below the threshold are not emitted. The threshold gate is owned
by the script's `THRESHOLDS` constant — meta-only; consumers cannot edit it. (The
consumer-available per-plan emitter gates via its own `marshal.json` knob; see
the shared contract below.)

## Emitted columns

```yaml
threshold: 3
plans_in_corpus: P    # plans that carried a findings directory
candidate_count: M
unattributed_excluded_count: K
rows[M]{module,finding_class,disposition,occurrence_count,plan_ids,severity}
```

| Column | Meaning |
|--------|---------|
| `candidate_count` | Number of promotable (module-attributed) candidate rows. |
| `unattributed_excluded_count` | Number of `default`-bucket recurrences that cleared the threshold but were declined promotion by the attribution gate. |
| `module` | The finding's concrete module attribution — always a real module (the `default` bucket is never surfaced). |
| `finding_class` | The collapsed finding signature (title prefix, lowercased). |
| `disposition` | The user-gate disposition (`suppressed`/`accepted`/`taken_into_account`). |
| `occurrence_count` | Number of distinct plans the tuple appears in. |
| `plan_ids` | `;`-joined plan ids contributing to the tuple. |
| `severity` | Always `genuine` — every surfaced row cleared the threshold and is module-attributed. |

Rows are ordered by descending `occurrence_count`, then by `module`,
`finding_class`, `disposition`.

## How the orchestrator interprets the rows

Each candidate row is a **preference-enrichment input** routed to
`architecture enrich`. Every surfaced row is already threshold-gated AND
module-attributed (the script RAN both gates — applying, for authorship, the
shared rule implemented in
`manage-findings/scripts/_preference_admissibility.py`), so
SKILL.md Step 4c routes EVERY surfaced row to its concrete module — there is no
further gating in the LLM body, and no row routes to the `default` bucket. The
generalization rule (tuple → best-practice / insight string), the routing target
(`architecture enrich … --module {module}` for the row's concrete module), and
the "generalize, do not log raw dispositions" privacy invariant are owned ONCE by
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
  derivation, and the threshold gate; the shared module
  `manage-findings/scripts/_preference_admissibility.py` is the single source of
  truth for the authorship-admissibility rule the script applies. Do not
  re-aggregate dispositions in chat.
- This check is read-only; it never edits `.plan/` files.
- **Generalize, do not log raw dispositions** — when routing surfaced rows to
  `architecture enrich`, never persist per-finding hash IDs or raw disposition
  rows; persist only the generalized hint string per the shared contract.
