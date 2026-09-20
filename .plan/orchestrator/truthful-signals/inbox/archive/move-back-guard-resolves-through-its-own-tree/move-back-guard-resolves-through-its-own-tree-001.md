envelope_version=1
sender_type=plan
sender_id=move-back-guard-resolves-through-its-own-tree
epic=truthful-signals
kind=candidate-lesson
created=2026-08-27T18:48:34Z

component=plan-marshall:manage-lessons
category=bug
confidence=high
source_plan=move-back-guard-resolves-through-its-own-tree
source_pr=1361

# manage-lessons add returns success for a lesson with no body

## Context

Five lessons were recorded during this run (2026-08-27-07-001, -07-002, -09-001, -12-001, -12-002), each naming a live defect in merged main. All five were title-and-metadata stubs with **empty bodies**. `manage-lessons add` allocates "metadata + title, empty body" by design and `set-body` is a separate verb; the `--rule` text passed at add time landed in metadata, not in the body. Every one of the five calls returned `status: success`.

The defect was caught only because the project `finalize-step-lessons-housekeeping` step happened to cross-check two sanctioned read paths (`list --full` and `get`) and noticed the bodies were empty. Nothing in the recording path itself signalled anything. All five were backfilled via `set-body` (2342 / 2255 / 2480 / 1978 / 1773 bytes).

## Root cause

The two-call path-allocate flow (`add` → `Write` body → `set-body`) is documented as canonical, but the first call is individually indistinguishable from a completed recording: it returns `status: success` and a `path`, and the lesson file exists on disk and lists in `manage-lessons list`. There is no state in which a caller is told "this lesson is not yet usable". A caller that believes `--rule` / `--title` carried the content has no feedback loop that disagrees.

This is the same failure shape the epic is named for: a confident success signal over an incomplete result.

## Proposed action

Two options, in preference order:

1. Add `manage-lessons add --body-file PATH` so allocation and body land in one call, collapsing the two-call flow to one. `--body-file` mirrors the existing `set-body --file` contract, so the shell-safety property is preserved.
2. Failing that, make the empty-body state legible: have `add` return `body_state: empty` (and `list` surface `body_bytes: 0`), so a body-less lesson is visibly incomplete rather than visibly successful.

Either way, a lesson with a zero-byte body should not be reported by any read verb as an ordinary active lesson without a discriminator.

## Evidence

- decision.log 22fa60 (2026-08-27T13:27:31Z) — "all 5 lessons this run recorded were title-and-metadata stubs with EMPTY BODIES … Five lessons naming live defects in merged main would have been unactionable to any later plan that consulted them"
- aspect: llm_to_script_opportunities — candidate "Allocate a lesson then populate its body as two separate calls", repetition_count 5, complexity low
- aspect: chat_history_analysis — the housekeeping step "reported at the strength its evidence supported rather than asserting or dismissing", which is why the defect surfaced at all
