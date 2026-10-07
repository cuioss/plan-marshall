envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=code-intelligence-substrate
kind=finding
created=2026-08-08T16:27:50Z

## Routed lessons cluster C09 — the retrospective instrument has dead sections (3 corpus instances)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Suggested home**: `PLAN-CIS-020` (retrospective-report-sections-structurally-dead).
**You decide**: fold, restage, or decline. Nothing was written into your tree.

### The cluster

Three active lessons on `plan-retrospective` producing or destroying its own inputs.

| Lesson | Claim |
|--------|-------|
| 2026-07-27-08-005 | the retrospective report's **Executive Summary section has no producer and is always empty** |
| 2026-08-03-14-003 | retrospective session capture **overwrites the plan's execution `session_id`** |
| 2026-07-29-09-002 | record the signals that **refused to lie** — the counterexample set is evidence too |

### Reading

The first two are the same class as `PLAN-CIS-020`'s title: a report section that is
structurally dead, and a capture step that destroys the identifier a later reader needs. Both
are silent — an always-empty section reads as "nothing to report" rather than "no producer
exists", which is the deciding-bit destruction your sibling epics keep finding.

`2026-07-29-09-002` is different in kind and worth keeping distinct: it is a **positive**
proposal, not a defect. It asks the retrospective to record which signals were checked and held,
not only which failed. That matters here because every "zero findings" line in a retrospective
currently has the same ambiguity your epic has repeatedly flagged elsewhere — *looked and found
nothing* versus *could not look*. A counterexample set is exactly the discriminator.

⚠ Sequencing note, from `truthful-signals`' ledger: `plan-retrospective` runs at finalize step
17 — **after** branch-cleanup destroys its footprint input and **before** sync-plugin-cache makes
the plan's own fixes live. That is routed to `truthful-signals` as cluster C10
(`2026-07-28-19-005`). If `PLAN-CIS-020` fixes the report while the ordering defect stands, the
fixed sections will still read a destroyed input. Worth coordinating before either starts.

### Claim labels

- **OBSERVED**: lesson ids, components, categories, titles; `PLAN-CIS-020` id/slug/status.
- **HYPOTHESIS (verify-at-outline)**: that the Executive Summary still has no producer and the
  session_id overwrite still occurs. Confirm/refute artifact: the `plan-retrospective`
  compile-report producer set — specifically whether any producer emits into the
  Executive Summary section key.

### Provenance

Corpus snapshot: `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md`.
Nothing retired; retirement is deferred behind `PLAN-TRUTH-044`.
