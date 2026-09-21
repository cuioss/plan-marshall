envelope_version=1
sender_type=plan
sender_id=derive-the-partition-and-the-budget-attribution
epic=test-quality
kind=candidate-lesson
created=2026-08-25T08:57:41Z

component=plan-marshall:manage-logging
category=bug
confidence=high
source_plan=derive-the-partition-and-the-budget-attribution

# Fix read --phase: over-filters the decision log, no-ops on the work log

## Context

`manage-logging` documents `read --plan-id P --type {work|decision|script} [--phase PHASE]`, with the note "`--phase` filters only `work` and `decision` log reads". Both filtered reads are wrong, in opposite directions:

- `read --type decision --phase 5-execute` returned `total_entries: 0`. The plan has 126 decision entries, many of them explicitly emitted by `(plan-marshall:phase-5-execute)` call sites.
- `read --type work --phase 5-execute` returned `total_entries: 541` — the unfiltered total — and the 60 shown span both 5-execute and 6-finalize.

So the same flag excludes everything on one log and does nothing on the other. Neither behaviour is the documented one.

The decision-log direction is the dangerous one: a consumer asking "what did phase 5 decide?" receives a clean, well-formed `status: success` with an empty result set. That is a could-not-look outcome wearing the shape of a measured zero.

## Root cause

Not established from the outside. The observable is that the phase discriminator the filter matches on is not the one either log actually carries: decision entries are written with a `(component:sub)` prefix and no phase field, so a phase predicate matches none of them; work entries appear not to be filtered at all.

## Proposed action

Either implement the filter against a discriminator both logs actually carry, or withdraw `--phase` from the read surface and say so. What must not remain is a documented filter that returns a well-formed empty set for a phase with 126 entries — a consumer cannot distinguish that from a real absence.

If the filter is kept, `total_entries` should report the filtered population so an unfiltered echo cannot masquerade as a filtered one.

## Evidence

- aspect: logging_gap_analysis — both reads performed during this retrospective; both results recorded
- `read --type decision --phase 5-execute` -> `total_entries: 0`; `read --type decision --limit 86` -> 126 entries including 20+ from phase-5 call sites
- `read --type work --phase 5-execute` -> `total_entries: 541`, identical to `analyze-logs` `counts.work_entries: 541`
