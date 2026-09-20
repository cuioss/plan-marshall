envelope_version=1
sender_type=plan
sender_id=plan-203-inbox-consumed-vs-missing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T09:34:48Z

component=plan-marshall:marshall-orchestrator
category=bug
title=Five emitted verb-output counts are LLM-tallied from free-text prose and cannot be checked

# Five emitted verb-output counts are LLM-tallied from free-text prose and cannot be checked

STAGED by PLAN-203's D4 gate, not fixed. Surfaces: `workflow/analyze.md`, `workflow/close.md`,
`workflow/resume.md` (verb output contracts).

## Observation

Five counts emitted in orchestrator verb output contracts have **no machine source** and are tallied
by the LLM from unstructured `epic.md` prose:

| Count | Verb |
|-------|------|
| `defects_added` | `analyze` |
| `watches_added` | `analyze` |
| `queue_items_retired` | `analyze` |
| `carried_forward_leads` | `close` |
| `reconciliations` | `resume` |

`Open Defects` and `Watches` are **free-text bullet lists**, so any count over them is **asserted,
never derived, and cannot be checked** by the reader who receives it.

## Contrast — the sibling counts in the same blocks ARE derivable

`orchestrate.md` `staged` / `launched` / `shipped`, `parallelization_scope`, `launched_count`;
`close.md` `plans_shipped` / `plans_parked`; `resume.md` `plans_launched` / `plans_staged` (all
`status.json` `plans[]` tallies); and `analyze.md` `messages_scanned` / `archived` / `invalid` /
`archive_failed` — **now derivable via `inbox list` after PLAN-203's D2**. So the same output block mixes
checkable counts with unfalsifiable ones, at identical visual weight.

## Rule

Structuring `Open Defects` and `Watches` moves all five into the derivable column. Until then, an
emitted count whose source is prose should not be rendered alongside derived counts without saying so
— **a number's provenance is part of the number**.

Claim label: OBSERVED (first-party enumeration, D4 gate).
