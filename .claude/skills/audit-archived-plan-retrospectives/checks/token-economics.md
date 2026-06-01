# Check: token-economics (cross-plan)

Operationalizes the one-off token deep-dive captured in lesson
`2026-06-01-12-001` as a repeatable check. Joins each plan's per-phase token
spend (`work/metrics.toon`) to its footprint (`references.json::scope_estimate`,
affected/modified file count) and its `status.json::metadata` change_type, then
computes per-plan token shares and efficiency ratios and a **corpus-relative**
anti-pattern flag set. This is a cross-plan check: it emits one aggregate block
(per-plan rows + corpus aggregates + derived thresholds) rather than one row per
plan in isolation. The deterministic computation lives in `scripts/audit.py`
(`cross_token_economics` / `emit_token_economics_block`); this sub-document is the
interpretation guide.

## Inputs the check reads

For every plan carrying a parseable `work/metrics.toon`, the script joins three
structured inputs:

| Input | Field(s) read | Used for |
|-------|---------------|----------|
| `work/metrics.toon` | per-phase `total_tokens` (sections `1-init` … `6-finalize`), top-level `session_message_count` | total tokens, per-phase shares, execute-blindness, long-session |
| `references.json` | `scope_estimate`, `modified_files` / `affected_files` count | footprint (`files`), scope aggregate |
| `status.json::metadata` | `change_type` | change_type aggregate |
| `tasks/TASK-*.json` | file count | `tasks`, `tokens_per_task` |

The `metrics.toon` parse reuses `parse_metrics_toon` (per-phase sections) plus a
small top-level scalar reader for `session_message_count` (which lives above the
first `[phase]` section, so the phase parser does not capture it). The
change_type / scope_estimate join reuses the `PlanInputs` fields already
collected by `collect_inputs`. Plans without a parseable `metrics.toon` are
excluded from the corpus entirely — they carry no token signal and a zero total
would skew the distributions.

## Per-plan computation

For each plan the script computes:

| Quantity | Definition |
|----------|------------|
| `total_tokens` | Sum of every phase's `total_tokens` (gross — this check measures the whole 6-phase workflow tax, so it does NOT exclude retrospective spend the way the `metrics` / `token-efficiency-trend` checks do). |
| per-phase share | Each phase's `total_tokens` / `total_tokens`. |
| `tokens_per_file` | `total_tokens // files` (files = `modified_files` count, falling back to `affected_files`). |
| `tokens_per_task` | `total_tokens // tasks` (task count = `tasks/TASK-*.json`). |
| `session_message_count` | The top-level `metrics.toon` scalar. |
| `change_type`, `scope` | Joined from `status.json::metadata` and `references.json`. |
| `exec_metrics_blind` | True when the `5-execute` phase recorded `total_tokens == 0` — the sub-agent token-attribution gap (lesson `2026-06-01-11-002`). |

## Cross-plan computation

Beyond the per-plan rows the script computes:

- **Aggregates by `change_type` and by `scope_estimate`** — count, average
  tokens, average files, and corpus-amortized `tokens_per_file` per bucket. This
  is the "smaller changes are *less* efficient" inversion table from the lesson:
  big sweeps amortize the fixed overhead, small work cannot.
- **Corpus per-phase distribution** — each phase's tokens as a fraction of the
  whole-corpus token spend (`corpus_refine_share`, `corpus_outline_share`,
  `corpus_execute_share`, `corpus_finalize_share`). This is the lesson's
  "only X% of corpus tokens reach implementation" read-out.

## Dynamic-threshold rationale: computed from the live corpus each run

**This is the defining property of the check.** Every anti-pattern cut-point is
derived from the LIVE corpus distribution on each run via the `median` /
`percentile` helpers — NONE are read from the `THRESHOLDS` table and NONE are
hard-coded. The lesson's literal numbers (~450K floor, 2× planning, 30% outline
share, 600 messages) describe the *shape* of each anti-pattern, but the actual
comparison value floats with the corpus so the check stays honest as the corpus
evolves: a future corpus with a lower overhead floor flags relative to *that*
lower floor, not against a frozen constant that would silently stop firing (or
fire on everything).

The derived thresholds, each echoed in the emitted block so a flagged row is
self-describing:

| Threshold | Derivation | Anti-pattern (lesson §) |
|-----------|-----------|-------------------------|
| `floor_band_p10_tokens` | 10th-percentile of plan totals | A — fixed overhead floor |
| `median_total_tokens` | median plan total | big-spend-tiny-footprint |
| `small_footprint_p25_files` | 25th-percentile of non-zero file counts | A and big-spend (the "tiny footprint" side) |
| `median_planning_exec_ratio` | median of per-plan planning/execute ratios (execute-blind plans excluded) | B — planning ≫ execution |
| `outline_share_p75` | 75th-percentile of per-plan outline shares | C / outline-heavy |
| `refine_share_p75` | 75th-percentile of per-plan refine shares | refine-heavy |
| `finalize_share_p75` | 75th-percentile of per-plan finalize shares | C — finalize bloat |
| `long_session_p75_msgs` | 75th-percentile of non-zero session message counts | D — marathon sessions |

The only fixed inputs are the phase-name list and the structural
`exec_metrics_blind` predicate (execute total == 0) — a recording fact, not a
tunable.

## Anti-pattern flags (dynamically derived)

Per plan the script emits a `flags` list. Each flag annotates the plan's value
AND the floating cut-point it was measured against:

| Flag | Fires when | Mirrors |
|------|-----------|---------|
| `exec_metrics_blind` | `5-execute` total == 0 | E — metrics blindness |
| `fixed_overhead_floor` | total ≤ `floor_band_p10` AND files ≤ `small_footprint_p25` | A |
| `planning_gt_exec` | (execute measured) planning/execute ratio > `median_planning_exec_ratio` | B |
| `outline_heavy` | outline share ≥ `outline_share_p75` | C |
| `refine_heavy` | refine share ≥ `refine_share_p75` | (refine variant of C) |
| `finalize_heavy` | finalize share ≥ `finalize_share_p75` | C |
| `big_spend_tiny_footprint` | total ≥ `median_total` AND files ≤ `small_footprint_p25` | tokens/file inversion |
| `long_session` | session messages ≥ `long_session_p75` | D |

### Degenerate-corpus guard on the outlier flags

`fixed_overhead_floor` and `big_spend_tiny_footprint` are corpus-relative
**outlier** detectors, so they only fire when the plan-total distribution has a
genuine tail on the relevant side. In a near-uniform corpus the percentile band
collapses (`p10 == median == max`), and a naive `total ≤ p10` / `total ≥ median`
test would catch EVERY plan — the "fire on everything" failure the dynamic-
threshold rationale above exists to avoid. Each flag therefore carries a spread
guard derived from the same live corpus:

- `fixed_overhead_floor` fires only when the cheap decile sits strictly below the
  middle (`floor_band_p10 < median_total`) — there must be a real cheap tail.
- `big_spend_tiny_footprint` fires only when some plan outspends the median
  (`max_total > median_total`) — there must be a real high tail.

When the relevant tail is absent (a uniform corpus of near-identical plans) the
flag is suppressed: a corpus where every plan is the same is not a corpus of
outliers. `long_session` is naturally guarded the same way because plans that
record no `session_message_count` are excluded from both the p75 derivation and
the comparison, so a corpus with no recorded session lengths produces no
long-session flag.

### exec_metrics_blind annotates the floors

When a plan is `exec_metrics_blind` the flag is emitted FIRST and explicitly
annotates which downstream numbers it floors:
`exec_metrics_blind(5-execute=0;floors:tokens_per_*,planning_gt_exec)`. This is
mandatory: a blind plan's `total_tokens`, `tokens_per_file`, `tokens_per_task`,
and `planning_gt_exec` ratio are all computed on under-counted data (the heaviest
phase recorded zero), so every later number for that plan is a FLOOR, not a
measurement. The `planning_gt_exec` flag is consequently SUPPRESSED for blind
plans (its denominator is the missing execute total) — its absence on a blind row
is by-construction, not "this plan planned efficiently". The orchestrator must
read every blind plan's economics as a lower bound.

## Emitted columns

```
plans_in_corpus: K
floor_band_p10_tokens: <derived>
median_total_tokens: <derived>
small_footprint_p25_files: <derived>
median_planning_exec_ratio: <derived>
outline_share_p75: <derived>
refine_share_p75: <derived>
finalize_share_p75: <derived>
long_session_p75_msgs: <derived>
corpus_refine_share: <derived>
corpus_outline_share: <derived>
corpus_execute_share: <derived>
corpus_finalize_share: <derived>
genuine_signal_count: G
rows[K]{plan_id,change_type,scope,files,tasks,msgs,total_tokens,tokens_per_file,tokens_per_task,exec_blind,flags,severity}
by_change_type[C]{value,n,avg_tokens,avg_files,tokens_per_file}
by_scope[S]{value,n,avg_tokens,avg_files,tokens_per_file}
```

| Column | Meaning |
|--------|---------|
| `plan_id` | The scanned plan's directory basename (rows sorted by total tokens, desc). |
| `change_type` / `scope` | Joined change_type and scope_estimate. |
| `files` / `tasks` | Footprint and task count (the amortization denominators). |
| `msgs` | `session_message_count`. |
| `total_tokens` | Gross sum across all phases. |
| `tokens_per_file` / `tokens_per_task` | Efficiency ratios (a FLOOR when `exec_blind`). |
| `exec_blind` | `true` when `5-execute` recorded zero tokens. |
| `flags` | `;`-joined corpus-relative anti-pattern flags (empty for a clean plan). |
| `severity` | Uniform D1 severity column: `genuine` when the row carries any flag, else `informational`. |

`genuine_signal_count` equals the number of flagged rows. The threshold and
corpus-distribution summary lines above the table carry the derived cut-points so
each flagged row is self-describing.

## How the orchestrator interprets the rows

This check is the repeatable form of the analysis adjudicated in lesson
`2026-06-01-12-001`. That lesson is already filed and `status=active`, so a
running audit's job is to track whether the corpus is moving toward or away from
its findings, NOT to re-file it:

- **`fixed_overhead_floor` / `big_spend_tiny_footprint`** — the largest lever
  (anti-pattern A). A plan flagged here paid the non-amortizing 6-phase tax on a
  tiny change. Surface it; the remediation (a lightweight track for surgical
  plans) is already named in the lesson's remediation directions — a *new*
  recurrence on a plan created AFTER a lightweight-track plan ships is the signal
  worth a Gate-1 dedup/extend against `2026-06-01-12-001`.
- **`planning_gt_exec` / `outline_heavy` / `refine_heavy`** — planning outspent
  execution (anti-pattern B). Cross-read with `scope-estimate-accuracy`: a
  surgical-scope plan that is planning-heavy is the prime lightweight-track
  candidate.
- **`finalize_heavy`** — anti-pattern C. Caveat per the lesson: gross finalize
  here INCLUDES retrospective spend that the `metrics` check excludes, so a high
  finalize share may be the retrospective itself, not pipeline bloat —
  cross-read the `metrics` check's (retrospective-excluded) finalize share before
  concluding.
- **`long_session`** — anti-pattern D. A marathon session on a small change
  re-loads accumulated context every turn; cross-read with the session-handoff
  gap (`2026-05-31-20-003`).
- **`exec_metrics_blind`** — anti-pattern E. Read every other number for that
  plan as a floor (see the annotation rule above). The blindness is the
  prerequisite fix (`2026-06-01-11-002`); until it lands the corpus totals
  under-count the heaviest phase.
- **corpus distribution / aggregate tables** — informational context. The
  "X% of corpus tokens reach `5-execute`" line and the tokens/file inversion
  table are the lesson's headline numbers recomputed live; a meaningful drift in
  either (execute share rising, tokens/file inversion flattening) is the
  process-improvement signal the check exists to surface over time.

## Adjudication against lesson 2026-06-01-12-001

The lesson `2026-06-01-12-001` is the canonical, already-filed source of this
check's anti-pattern taxonomy (its remediation direction #5 explicitly proposes
"so this analysis becomes a repeatable check rather than a one-off" — this check
IS that). Consequences for Step 4 lesson filing:

1. **Do NOT re-file the lesson.** A flagged row here is COVERED by
   `2026-06-01-12-001` on a Gate-1 dedup basis — name that lesson ID as the
   covering reference and stop. Re-filing the same token-economics finding is the
   prohibited "assumption is not verification" anti-pattern in reverse: the
   coverage IS verified (this check's flag set is literally derived from the
   lesson's anti-patterns).
2. **A genuinely NEW signal is a corpus *drift*, not a repeat flag.** The
   file-worthy signal is movement: the corpus execute-share falling further, a
   new fixed-overhead recurrence on a plan created after a remediation shipped, or
   a previously-unflagged anti-pattern (e.g. `1-init` bloat, anti-pattern F)
   becoming systemic. Such a drift extends `2026-06-01-12-001` via Gate-1
   `merge_into`, it does not open a parallel lesson.
3. **Blind-plan floors are caveated, not findings.** An `exec_metrics_blind` plan
   contributes a FLOOR; do not adjudicate its `tokens_per_file` as a precise
   finding. The blindness itself is covered by `2026-06-01-11-002`.

## Critical rules

- The script is the single source of truth for every per-plan number, every
  corpus aggregate, and every derived threshold. Do not re-join `metrics.toon` to
  `references.json` or re-derive a cut-point in chat.
- Every threshold is corpus-relative (`median` / `percentile` over the live
  corpus). There are NO hard-coded magic numbers in the check. If the derivation
  itself must change, edit `scripts/audit.py` rather than substituting a fixed
  number in a reading.
- `exec_metrics_blind` floors are mandatory to annotate: a blind plan's
  downstream numbers are lower bounds, and `planning_gt_exec` is suppressed for
  blind plans by construction.
- This check is read-only; it never edits `.plan/` files.
