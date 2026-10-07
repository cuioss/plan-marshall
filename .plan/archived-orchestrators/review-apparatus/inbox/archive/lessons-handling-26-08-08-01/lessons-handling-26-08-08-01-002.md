envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=review-apparatus
kind=finding
created=2026-08-08T16:27:21Z

## Routed lessons cluster C06 — the in-house gates were silent where they claim coverage (14 corpus instances)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Why you**: PR/review routing test fires first and wins outright.
**Suggested home**: `PLAN-PR-011` (review-bots-catch-what-in-house-gates-cannot) — the plan is
literally named for this cluster and, as far as I can see from your `status.json`, has no
empirical corpus attached to it. This is that corpus.
**You decide**: fold, restage, or decline. Nothing was written into your tree.

### The cluster

Fourteen active lessons, every one of which ends in some form of *"all in-house gates passed,
only the PR bot caught it"*. They are not one defect — they are fourteen independent
observations of the same structural gap, which is exactly what makes them a rate rather than
an anecdote.

| Lesson | The gate that was silent |
|--------|--------------------------|
| 2026-06-22-11-001 | doc prose mis-described a completion condition (acknowledged vs submitted) |
| 2026-06-22-12-001 | a placeholder-bearing constraint-bounded string was length-checked against its literal form, not its worst-case expansion |
| 2026-06-22-13-001 | local ruff `select` omits the RUF family — RUF002 slips every in-house gate |
| 2026-06-25-02-001 | non-portable tokens (dates, versions, machine paths) in doc prose; no in-house gate enforces the convention |
| 2026-06-25-10-001 | prose paraphrased a machine-readable universe instead of enumerating it |
| 2026-06-30-15-001 | unsorted filesystem traversal feeding analyzer output is non-deterministic across runs |
| 2026-07-08-09-001 | `shutil.copyfile` into a symlinked destination writes through the stale link |
| 2026-07-12-18-001 | a parsing boundary cannot distinguish absent from present-but-invalid |
| 2026-07-14-16-002 | the existing test always had the child present, so only the recursion branch was ever exercised |
| 2026-07-14-17-001 | presence check by narrow key hides a wrongly-shaped record; unfiltered external-API elements corrupt the payload |
| 2026-07-21-01-001 | analysis-report deliverables shipped structural and quantitative claims unverified and mutually inconsistent |
| 2026-07-21-12-001 | a canonical-key migration seam shipped legacy-key-blind and non-idempotent |
| 2026-07-22-10-001 | a loose doc placeholder became a type mismatch once a second group was added |
| 2026-06-24-14-003 | missing deterministic tie-break plus uncleared gate-trigger state — two functional-correctness bugs |

### Why this matters to your epic specifically

`PLAN-PR-011`'s thesis is that review bots catch a class in-house gates cannot. Fourteen
first-party instances let that be stated as a **measured class with a denominator** rather than
asserted. Two cautions, both from your own standing rules:

- ⚠ **This is a sample, not an enumeration.** It is fourteen lessons somebody chose to file, not
  every occurrence. Any rate derived from it must publish that population and its provenance.
- ⚠ **The class is mixed.** At least three members (RUF select, unsorted traversal, symlink
  copy) are *addable in-house gates*; others (doc prose semantics, report-claim consistency) may
  be genuinely bot-only. Partitioning by "could an in-house gate have caught this" before
  computing anything is the same partition-before-rate discipline your `PLAN-PR-006` D1 already
  owes for the absence corpus.

There is an overlapping plan in `truthful-signals`: `PLAN-TRUTH-019` (build-gate-coverage-parity).
If those two are the same population viewed differently, better to say so than to ship both.

### Claim labels

- **OBSERVED**: lesson ids, components, categories, titles; `PLAN-PR-011` id/slug/status.
- **HYPOTHESIS (verify-at-outline)**: that each gap is still open. Confirm/refute artifact: each
  named gate's own scan scope — e.g. the `ruff` `select` list in the pyprojectx config for
  2026-06-22-13-001.

### Provenance

Corpus snapshot: `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md`.
Nothing retired; retirement is deferred behind `PLAN-TRUTH-044`.
