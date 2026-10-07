envelope_version=1
sender_type=plan
sender_id=sweep-preambles-shipped-accessors
epic=test-quality
kind=candidate-lesson
created=2026-09-08T01:46:01Z

# Dedup keys on component spelling, so one defect was filed four times

Re-routed from the global lessons store as `2026-09-08-01-002`. It was filed there
because the finalize dispatcher asserted `orchestrated: false` without running the
orchestration-detection seam; the seam reports `orchestrated: true, epic: test-quality`
for this plan's `source_id`. The global-store copy is the same content.

## Context

The active lessons corpus holds **four** lessons describing the same defect —
`baseline-reconcile` scraping localized `git merge-tree` prose and manufacturing spurious
conflict findings:

| id | component as filed | title |
|----|--------------------|-------|
| `2026-09-03-19-001` | `plan-marshall:workflow-integration-git` | counts merge-tree informational lines as conflicted files |
| `2026-09-04-07-001` | *(empty)* | mis-parses localized git merge-tree output as extra conflicts |
| `2026-09-04-17-011` | `plan-marshall:workflow-integration-git` | parses localized git prose as file paths, files spurious blocking findings |
| `2026-09-07-21-001` | `plan-marshall:workflow-integration-git:baseline-reconcile` | conflict parser misreads localized git merge-tree output |

Four runs, four filings, one unfixed defect. The fourth was filed by
`sweep-preambles-shipped-accessors`, whose Gate 1 dedup pass matched none of the three.

## Root cause

Gate 1 classifies a candidate by **component + root cause**. The root cause is identical
across all four; the component is not — it has been written three ways for one script:
the skill (`plan-marshall:workflow-integration-git`), skill-plus-script
(`…:baseline-reconcile`), and the empty string.

The empty-component case is a separate known failure: lesson `2026-09-03-22-002` records
that lessons carrying YAML frontmatter are listable but unaddressable by every id-keyed
verb, and six corpus lessons currently list with an empty `component`. Those are invisible
to a `--component`-filtered dedup query by construction.

So the key has two independent ways to miss — a legitimate spelling variation, and records
whose component does not survive listing. Both were exercised here.

## Proposed action

1. **Normalize the component before comparing.** Compare on the *skill* component
   (`bundle:skill`), truncating any `:script` third segment. A defect in `bundle:skill:script`
   is a defect in `bundle:skill`.
2. **Do not let an unreadable component silently narrow the dedup population.** When any
   active lesson lists with an empty component, the filtered query has not seen the whole
   corpus — include those records, or report the gap, applying the same could-not-look
   discipline this system applies to a zero elsewhere.
3. **Add a title/root-cause similarity fallback.** Component equality is a cheap primary key,
   not a sufficient one; a root-cause comparison would have caught all three prior filings.
4. **Consolidate the existing four** via `supersede` so the recurrence count is visible on one
   record and the eventual fix retires one entry rather than four.

## Why this matters beyond the one duplicate

The corpus is the system's memory, and 141 active lessons is past the size where anyone reads
all of it. A dedup gate that misses on a spelling variation turns every recurrence into corpus
growth instead of corpus signal — the opposite of its purpose. It also makes retire-on-fix
unreliable: fixing `baseline-reconcile` now means finding four records under three component
keys, and missing one leaves a stale lesson asserting a closed defect.

## Evidence

- `manage-lessons list` over the 141 active lessons — the four rows above
- `references/dedup-analysis.md` — Gate 1 compares by component + root cause
- lesson `2026-09-03-22-002` — empty-component lessons are unaddressable by id-keyed verbs
