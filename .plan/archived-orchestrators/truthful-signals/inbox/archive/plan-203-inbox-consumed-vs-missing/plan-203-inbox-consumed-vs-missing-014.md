envelope_version=1
sender_type=plan
sender_id=plan-203-inbox-consumed-vs-missing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T10:22:46Z

# check-artifact-consistency counts intent=read gate inputs as declared write targets

component: plan-marshall:plan-retrospective
category: bug
confidence: high
source: plan-retrospective (plan-203-inbox-consumed-vs-missing)

## Context

PLAN-203 declared 13 affected files. Five were never touched:

- `marshall-orchestrator/templates/epic.md`
- `marshall-orchestrator/workflow/orchestrate.md`
- `marshall-orchestrator/workflow/analyze.md`
- `marshall-orchestrator/workflow/close.md`
- `persona-marshall-orchestrator/standards/orchestration-model.md`

All five are deliverable 4's affected_files, and deliverable 4 is an explicit
**mutates-nothing gate** whose every `affected_files` entry carries `"intent": "read"`. Its own
verification criterion is `git status --porcelain -- marketplace/ test/` producing empty output. The
plan behaved exactly as specified.

`check-artifact-consistency` nevertheless emitted `affected_files_exact_match` with those five under
`outline_only[]` and forwarded a set mismatch to the manifest aspect.

## Root cause

The outline stores `affected_files` as structs with a per-file `intent` (`write-replace` vs `read`).
`references.json` flattens them to a bare path list, discarding `intent`. By the time the consistency
check reads the declared set, a read-only gate input is indistinguishable from an unfulfilled write
target.

## Proposed action

1. Read the declared set from the solution outline's `affected_files` structs (via
   `manage-solution-outline list-deliverables`) rather than from the flattened `references.json` list,
   and compare only `intent: write-replace` entries against the realized footprint.
2. Alternatively, carry `intent` through into `references.json`.
3. Report `intent: read` declarations in a separate, non-grading `gate_inputs[]` block so the
   information is preserved without polluting the coverage grade.

## Evidence

- `manage-solution-outline list-deliverables` — deliverable 4, all seven affected_files `"intent": "read"`
- references.json — flat 13-element `affected_files` array, no intent
- fragment-artifact-consistency.toon — `affected_files_exact_match.outline_only[13]`
- Verification criterion of deliverable 4: "the command's output is empty for this deliverable's task
  (the gate mutated nothing)"
