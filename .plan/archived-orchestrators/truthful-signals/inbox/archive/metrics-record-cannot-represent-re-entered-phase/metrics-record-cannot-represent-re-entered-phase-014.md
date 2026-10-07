envelope_version=1
sender_type=plan
sender_id=metrics-record-cannot-represent-re-entered-phase
epic=truthful-signals
kind=finding
created=2026-08-09T21:30:12Z

# Finding: a pre-change NINE-column dispatch-boundary row now reads as MEASURED ZERO — the legacy rescue covers five-column rows only

**Kind**: finding (live defect in merged main; requires orchestrator scheduling, not corpus filing)
**Source**: PLAN-TRUTH-055 post-landing retrospective, read against the contract PR #1129 itself shipped
**Surface**: `manage-metrics/standards/data-format.md` § Per-Dispatch Context-Load Attribution; `plan-retrospective/scripts/analyze-logs.py` `_parse_dispatch_boundary_file`

## The defect

PR #1129 made an omitted context-load flag write the literal `unmeasured` instead of `0`, and defined a
**three-way** cell read: an integer is *measured* (including a measured `0`), the token `unmeasured` is
*deliberately not measured*, anything else is *unrecognised*.

It also defined a backward-compatibility path — but scoped to the wrong population:

> "A legacy five-column row (written before the columns existed) still parses — the reader uses a
> `len(parts) >= 5` floor — and its four missing columns read as **unmeasured**."

That rescue covers rows written before the four columns existed. It does **not** cover rows written
*after* the columns existed and *before* the `unmeasured` token existed. Those rows are **nine columns
wide** and carry the old writer's literal `0` defaults in cells 6-9. The `len(parts) >= 5` floor passes
them through intact, and the three-way read then classifies each `0` as a **measured zero**.

## First-party evidence, from this plan's own store

`work/metrics-dispatch-boundaries-4-plan.toon`, appended at `2026-08-09T08:03:02Z` — before the fix
landed in the worktree:

```text
rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms,input_tokens,output_tokens,cache_read_input_tokens,cache_creation_input_tokens}:
2026-08-09T08:03:02Z,task_batch_complete,239871,87,683289,0,0,0,0
```

**The mis-read is confirmed empirically, not inferred.** `analyze-logs`, run during this retrospective
against merged-main code, reported for that row:

```text
unmeasured_columns: []
```

— i.e. it asserted all four context-load columns were measured — while correctly reporting all four as
`unmeasured` on the 12 post-change rows in the same plan. One plan's ledger, two schemas, and the
reader silently claims a measurement on the older half.

A dispatch that consumed 239,871 tokens across 87 tool uses did not load zero context. That is the
originating spec's own argument (`cache_read: 0` is *impossible* for a dispatch that consumed 541,951
tokens) — reproduced one layer down, and now certified as measured rather than merely defaulted.

## Blast radius

Every dispatch-boundary row written between the four columns' introduction and PR #1129 (2026-08-09),
across the whole archived corpus. The originating spec measured **19 such rows on one plan** and
described them as uniformly zero; under the shipped reader every one of those 19 is now a *measured*
zero. The corpus did not get more honest for those rows — it got more confidently wrong, because the
zeros now carry an affirmative reading they previously lacked.

This matters disproportionately because these four columns are, per the spec, **the only per-dispatch
view of context load**, and context load is where the cost is.

## Proposed remedy

A fourth state, following the precedent this same plan already set. PR #1129 shipped a **three-state
old-schema read** for the renamed partiality keys (`current` / `old-schema` / `pre-#812`) precisely
because archived records are immutable history and an absent key must not read as a clean verdict. The
ledger row needs the same treatment:

- a schema marker on the boundary file, **or**
- a cutoff keyed on the row timestamp against the #1129 landing,

so a nine-column row written by the pre-change writer reads as **unmeasured**, not as measured zero.

Note the asymmetry worth preserving: the legacy-five rescue was *right* to read absence as unmeasured.
The gap is that "wrote a default" and "wrote a measurement" became indistinguishable at exactly the
moment the schema stopped changing width.

## Cross-reference

Same family as this plan's own D3, and it is the residue D3 left. `PLAN-TRUTH-066` is already
sequenced next on `manage-metrics` — this is a candidate for it rather than a new plan, if its scope
admits a reader-side migration.
